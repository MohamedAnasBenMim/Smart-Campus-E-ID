package com.smartcampus.backend.service;

import com.smartcampus.backend.dto.AccessDecision;
import com.smartcampus.backend.dto.FaceServiceResult;
import com.smartcampus.backend.model.Alerte;
import com.smartcampus.backend.model.Classe;
import com.smartcampus.backend.model.Cours;
import com.smartcampus.backend.model.EvenementAcces;
import com.smartcampus.backend.model.Personne;
import com.smartcampus.backend.model.RegleAcces;
import com.smartcampus.backend.model.RegleAccesRole;
import com.smartcampus.backend.repository.AlerteRepository;
import com.smartcampus.backend.repository.ClasseRepository;
import com.smartcampus.backend.repository.CoursRepository;
import com.smartcampus.backend.repository.EvenementAccesRepository;
import com.smartcampus.backend.repository.PersonneRepository;
import com.smartcampus.backend.repository.RegleAccesRepository;
import com.smartcampus.backend.repository.RegleAccesRoleRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.time.DayOfWeek;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * BF-08 / BF-09 — Reçoit une frame + une zone, appelle le service de
 * reconnaissance, croise le résultat avec les règles d'accès, décide,
 * puis journalise systématiquement.
 *
 * NOUVEAU — DÉCISION D'ACCÈS À 3 NIVEAUX, dans cet ordre :
 *   1. Règle INDIVIDUELLE (RegleAcces) — exception ponctuelle pour une
 *      personne précise, rare, prioritaire sur tout le reste.
 *   2. Règle par RÔLE (RegleAccesRole) — accès général pour tout un
 *      rôle (typiquement le personnel sans emploi du temps de cours :
 *      surveillants, direction...).
 *   3. COURS EN COURS, pour ÉLÈVES et PROFS uniquement — la personne
 *      a-t-elle, en ce moment précis, un cours dans CETTE salle ?
 *      Remplace le besoin de créer une règle manuelle pour chacune des
 *      centaines d'élèves/profs d'un établissement.
 *
 * Si AUCUN de ces 3 niveaux ne couvre la situation → REFUS PAR DÉFAUT.
 * C'est ce refus par défaut qui protège naturellement les zones
 * sensibles (ex. bureau du directeur) : sans règle explicite qui
 * l'autorise, personne n'y entre, pas besoin de liste d'interdiction.
 */
@Service
public class AccessDecisionService {

    private static final Logger log = LoggerFactory.getLogger(AccessDecisionService.class);

    private static final Set<String> RESULTATS_IGNORES = Set.of(
            "detection_incertaine", "angle_trop_marque"
    );

    private static final Color COULEUR_PROBLEME = new Color(214, 69, 80);
    private static final Color COULEUR_ACCORDE = new Color(14, 143, 107);

    private static final Duration COOLDOWN_ALERTE = Duration.ofMinutes(5);

    // NOUVEAU — cooldown sur la JOURNALISATION elle-même (pas juste les
    // alertes) : sans lui, une personne immobile devant la caméra avec
    // un problème persistant (ex. visage trop petit) crée une nouvelle
    // ligne d'événement à CHAQUE frame analysée — plusieurs par
    // seconde, rendant l'historique illisible. Fenêtre volontairement
    // courte (30s, pas 5 minutes comme les alertes) : on veut quand
    // même des horodatages relativement frais pour la présence, juste
    // pas un doublon par seconde.
    private static final Duration COOLDOWN_EVENEMENT = Duration.ofSeconds(30);
    private final Map<String, Instant> derniersEvenements = new ConcurrentHashMap<>();

    private final Map<String, Instant> dernieresAlertes = new ConcurrentHashMap<>();

    private final FaceServiceClient faceServiceClient;
    private final PersonneRepository personneRepository;
    private final RegleAccesRepository regleAccesRepository;
    private final RegleAccesRoleRepository regleAccesRoleRepository;
    private final CoursRepository coursRepository;
    private final ClasseRepository classeRepository;
    private final EvenementAccesRepository evenementAccesRepository;
    private final AlerteRepository alerteRepository;

    public AccessDecisionService(
            FaceServiceClient faceServiceClient,
            PersonneRepository personneRepository,
            RegleAccesRepository regleAccesRepository,
            RegleAccesRoleRepository regleAccesRoleRepository,
            CoursRepository coursRepository,
            ClasseRepository classeRepository,
            EvenementAccesRepository evenementAccesRepository,
            AlerteRepository alerteRepository
    ) {
        this.faceServiceClient = faceServiceClient;
        this.personneRepository = personneRepository;
        this.regleAccesRepository = regleAccesRepository;
        this.regleAccesRoleRepository = regleAccesRoleRepository;
        this.coursRepository = coursRepository;
        this.classeRepository = classeRepository;
        this.evenementAccesRepository = evenementAccesRepository;
        this.alerteRepository = alerteRepository;
    }

    public List<AccessDecision> processFrame(MultipartFile image, String zoneId) throws IOException {
        FaceServiceResult result = faceServiceClient.recognize(image);
        List<AccessDecision> decisions = new ArrayList<>();

        byte[] imageBytesOriginaux = image.getBytes();
        String typeContenu = image.getContentType() != null ? image.getContentType() : "image/jpeg";

        for (FaceServiceResult.FaceResultItem face : result.getResultats()) {
            if (RESULTATS_IGNORES.contains(face.getResultat())) {
                continue;
            }

            if ("spoof_detecte".equals(face.getResultat())) {
                String capture = annoterImage(imageBytesOriginaux, typeContenu, face.getBbox(), "SPOOFING", COULEUR_PROBLEME);
                decisions.add(handleSpoof(zoneId, capture));
                continue;
            }

            if ("inconnu".equals(face.getResultat())) {
                String capture = annoterImage(imageBytesOriginaux, typeContenu, face.getBbox(), "INCONNU", COULEUR_PROBLEME);
                decisions.add(handleInconnu(zoneId, capture, face.getEmbedding()));
                continue;
            }

            if ("reconnu".equals(face.getResultat())) {
                decisions.add(handleReconnu(
                        face.getSubjectId(), zoneId, face.getAvertissement(),
                        imageBytesOriginaux, typeContenu, face.getBbox(), face.getEmbedding()
                ));
            }
        }

        if (result.isPresenceNonIdentifiee()) {
            String capture = "data:" + typeContenu + ";base64," + Base64.getEncoder().encodeToString(imageBytesOriginaux);
            decisions.add(handlePresenceNonIdentifiee(
                    zoneId, result.getPersonnesDetectees(), result.getVisagesDetectes(), capture
            ));
        }

        return decisions;
    }

    /**
     * NOUVEAU — détermine si un NOUVEL événement doit être écrit en
     * base, ou si on est encore dans la fenêtre de cooldown d'un
     * événement strictement identique tout récent. Contrairement à
     * doitCreerAlerte(), s'applique à TOUS les événements (ACCORDE
     * comme REFUSE), pas seulement ceux qui déclenchent une alerte.
     */
    private boolean doitJournaliser(String cle) {
        Instant maintenant = Instant.now();
        Instant dernier = derniersEvenements.get(cle);

        if (dernier != null && Duration.between(dernier, maintenant).compareTo(COOLDOWN_EVENEMENT) < 0) {
            return false;
        }

        derniersEvenements.put(cle, maintenant);
        return true;
    }

    private boolean doitCreerAlerte(String type, String zoneId, String personneId) {
        String cle = type + ":" + zoneId + ":" + (personneId != null ? personneId : "inconnu");
        Instant maintenant = Instant.now();
        Instant derniere = dernieresAlertes.get(cle);

        if (derniere != null && Duration.between(derniere, maintenant).compareTo(COOLDOWN_ALERTE) < 0) {
            log.info(
                    "[ALERTE] Ignorée (cooldown actif, {} restantes) : {}",
                    COOLDOWN_ALERTE.minus(Duration.between(derniere, maintenant)),
                    cle
            );
            return false;
        }

        dernieresAlertes.put(cle, maintenant);
        return true;
    }

    private String annoterImage(byte[] imageBytesOriginaux, String typeContenu, List<Integer> bbox, String etiquette, Color couleur) {
        if (bbox == null || bbox.size() < 4) {
            return encoderSansAnnotation(imageBytesOriginaux, typeContenu);
        }
        try {
            BufferedImage image = ImageIO.read(new ByteArrayInputStream(imageBytesOriginaux));
            if (image == null) {
                return encoderSansAnnotation(imageBytesOriginaux, typeContenu);
            }

            Graphics2D g = image.createGraphics();
            g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

            int x = bbox.get(0), y = bbox.get(1), largeur = bbox.get(2), hauteur = bbox.get(3);
            g.setColor(couleur);
            g.setStroke(new BasicStroke(4));
            g.drawRect(x, y, largeur, hauteur);

            if (etiquette != null) {
                g.setFont(g.getFont().deriveFont(Font.BOLD, 22f));
                FontMetrics fm = g.getFontMetrics();
                int largeurEtiquette = fm.stringWidth(etiquette) + 14;
                int hauteurEtiquette = fm.getHeight() + 6;
                int yEtiquette = Math.max(0, y - hauteurEtiquette);

                g.setColor(couleur);
                g.fillRect(x, yEtiquette, largeurEtiquette, hauteurEtiquette);
                g.setColor(Color.WHITE);
                g.drawString(etiquette, x + 7, yEtiquette + fm.getAscent() + 2);
            }

            g.dispose();
            ByteArrayOutputStream sortie = new ByteArrayOutputStream();
            ImageIO.write(image, "jpg", sortie);
            return "data:image/jpeg;base64," + Base64.getEncoder().encodeToString(sortie.toByteArray());

        } catch (IOException e) {
            log.warn("Échec de l'annotation d'image : {} — capture non annotée utilisée à la place", e.getMessage());
            return encoderSansAnnotation(imageBytesOriginaux, typeContenu);
        }
    }

    private String encoderSansAnnotation(byte[] imageBytesOriginaux, String typeContenu) {
        return "data:" + typeContenu + ";base64," + Base64.getEncoder().encodeToString(imageBytesOriginaux);
    }

    private AccessDecision handleSpoof(String zoneId, String capturePhoto) {
        String raison = "tentative de spoofing détectée";
        String cle = "SPOOFING:" + zoneId + ":inconnu";

        if (doitJournaliser(cle)) {
            EvenementAcces evt = journaliser(null, zoneId, "REFUSE", raison, capturePhoto);
            if (doitCreerAlerte("SPOOFING", zoneId, null)) {
                creerAlerte("SPOOFING", evt.getId(), capturePhoto, null);
            }
        }

        return new AccessDecision(null, null, zoneId, "REFUSE", raison);
    }

    private AccessDecision handleInconnu(String zoneId, String capturePhoto, List<Double> embedding) {
        String raison = "personne non enrôlée";
        String cle = "ACCES_NON_AUTORISE:" + zoneId + ":inconnu";

        if (doitJournaliser(cle)) {
            EvenementAcces evt = journaliser(null, zoneId, "REFUSE", raison, capturePhoto);
            if (doitCreerAlerte("ACCES_NON_AUTORISE", zoneId, null)) {
                creerAlerte("ACCES_NON_AUTORISE", evt.getId(), capturePhoto, embedding);
            }
        }

        return new AccessDecision(null, null, zoneId, "REFUSE", raison);
    }

    private AccessDecision handlePresenceNonIdentifiee(
            String zoneId, int personnesDetectees, int visagesDetectes, String capturePhoto
    ) {
        String raison = String.format(
                "%d personne(s) détectée(s) mais identité confirmée pour %d visage(s) seulement — présence non identifiée",
                personnesDetectees, visagesDetectes
        );
        String cle = "PRESENCE_NON_IDENTIFIEE:" + zoneId + ":inconnu";

        if (doitJournaliser(cle)) {
            EvenementAcces evt = journaliser(null, zoneId, "REFUSE", raison, capturePhoto);
            if (doitCreerAlerte("PRESENCE_NON_IDENTIFIEE", zoneId, null)) {
                creerAlerte("PRESENCE_NON_IDENTIFIEE", evt.getId(), capturePhoto, null);
            }
        }

        return new AccessDecision(null, null, zoneId, "REFUSE", raison);
    }

    private AccessDecision handleReconnu(
            String personneId, String zoneId, String avertissement,
            byte[] imageBytesOriginaux, String typeContenu, List<Integer> bbox, List<Double> embedding
    ) {
        Optional<Personne> personneOpt = personneRepository.findById(personneId);
        if (personneOpt.isEmpty()) {
            String capture = annoterImage(imageBytesOriginaux, typeContenu, bbox, "INCONNU", COULEUR_PROBLEME);
            return handleInconnu(zoneId, capture, embedding);
        }
        Personne personne = personneOpt.get();

        if (avertissement != null) {
            String raison = "identité probable (" + personne.getNom() + ") mais confiance réduite : " + avertissement;
            String capture = annoterImage(imageBytesOriginaux, typeContenu, bbox, "À CONFIRMER", COULEUR_PROBLEME);
            String cle = "IDENTITE_A_CONFIRMER:" + zoneId + ":" + personneId;

            if (doitJournaliser(cle)) {
                EvenementAcces evt = journaliser(personneId, zoneId, "REFUSE", raison, capture);
                if (doitCreerAlerte("IDENTITE_A_CONFIRMER", zoneId, personneId)) {
                    creerAlerte("IDENTITE_A_CONFIRMER", evt.getId(), capture, embedding);
                }
            }
            return new AccessDecision(personneId, personne.getNom(), zoneId, "REFUSE", raison);
        }

        // ============================================================
        // NOUVEAU — décision à 3 niveaux, remplace l'ancienne
        // vérification unique sur RegleAcces par personne.
        // ============================================================
        String raisonAcces = determinerAcces(personne, zoneId);

        if (raisonAcces == null) {
            String raison = "zone non autorisée pour ce profil";
            String cle = "ACCES_INTERDIT:" + zoneId + ":" + personneId;

            if (doitJournaliser(cle)) {
                String capture = annoterImage(imageBytesOriginaux, typeContenu, bbox, personne.getNom() + " — ZONE INTERDITE", COULEUR_PROBLEME);
                EvenementAcces evt = journaliser(personneId, zoneId, "REFUSE", raison, capture);
                if (doitCreerAlerte("ACCES_INTERDIT", zoneId, personneId)) {
                    creerAlerte("ACCES_INTERDIT", evt.getId(), capture, null);
                }
            }
            return new AccessDecision(personneId, personne.getNom(), zoneId, "REFUSE", raison);
        }

        String cleAccorde = "ACCORDE:" + zoneId + ":" + personneId;
        if (doitJournaliser(cleAccorde)) {
            String capture = annoterImage(imageBytesOriginaux, typeContenu, bbox, personne.getNom(), COULEUR_ACCORDE);
            journaliser(personneId, zoneId, "ACCORDE", raisonAcces, capture);
        }
        return new AccessDecision(personneId, personne.getNom(), zoneId, "ACCORDE", raisonAcces);
    }

    /**
     * Cœur de la nouvelle logique — retourne la raison de l'accès s'il
     * est autorisé (niveau 1, 2 ou 3), ou null si rien ne le couvre
     * (refus par défaut).
     */
    private String determinerAcces(Personne personne, String zoneId) {
        LocalTime maintenant = LocalTime.now();

        // Niveau 1 — règle INDIVIDUELLE (exception ponctuelle, rare)
        Optional<RegleAcces> regleIndividuelle = regleAccesRepository.findByPersonneIdAndZoneId(personne.getId(), zoneId);
        if (regleIndividuelle.isPresent() && horaireCouvre(maintenant, regleIndividuelle.get().getHoraireDebut(), regleIndividuelle.get().getHoraireFin())) {
            return "identité confirmée, règle individuelle validée";
        }

        // Niveau 2 — règle par RÔLE (personnel sans emploi du temps de cours)
        List<RegleAccesRole> reglesRole = regleAccesRoleRepository.findByRoleAndZoneId(personne.getRole(), zoneId);
        for (RegleAccesRole regle : reglesRole) {
            if (horaireCouvre(maintenant, regle.getHoraireDebut(), regle.getHoraireFin())) {
                return "identité confirmée, accès autorisé pour le rôle " + personne.getRole();
            }
        }

        // Niveau 3 — COURS EN COURS, pour élèves et profs uniquement
        if ("ELEVE".equals(personne.getRole()) || "PROF".equals(personne.getRole())) {
            if (aCoursMaintenant(personne, zoneId, maintenant)) {
                return "identité confirmée, cours en cours dans cette salle";
            }
        }

        // Aucun niveau ne couvre la situation → refus par défaut.
        return null;
    }

    private boolean horaireCouvre(LocalTime maintenant, LocalTime debut, LocalTime fin) {
        return !maintenant.isBefore(debut) && !maintenant.isAfter(fin);
    }

    /**
     * Vérifie si cette personne (élève ou prof) a, en ce moment
     * précis, un Cours programmé dans CETTE zone.
     */
    private boolean aCoursMaintenant(Personne personne, String zoneId, LocalTime maintenant) {
        String jourActuel = jourSemaineActuel();
        List<Cours> tousLesCours = coursRepository.findAll();

        if ("PROF".equals(personne.getRole())) {
            return tousLesCours.stream().anyMatch(c ->
                    personne.getId().equals(c.getProfId())
                            && zoneId.equals(c.getZoneId())
                            && jourActuel.equals(c.getJourSemaine())
                            && horaireCouvre(maintenant, c.getHeureDebut(), c.getHeureFin())
            );
        }

        if ("ELEVE".equals(personne.getRole())) {
            Optional<Classe> classeOpt = classeRepository.findAll().stream()
                    .filter(cl -> cl.getEleveIds() != null && cl.getEleveIds().contains(personne.getId()))
                    .findFirst();

            if (classeOpt.isEmpty()) {
                return false;
            }
            String classeId = classeOpt.get().getId();

            return tousLesCours.stream().anyMatch(c ->
                    classeId.equals(c.getClasseId())
                            && zoneId.equals(c.getZoneId())
                            && jourActuel.equals(c.getJourSemaine())
                            && horaireCouvre(maintenant, c.getHeureDebut(), c.getHeureFin())
            );
        }

        return false;
    }

    private String jourSemaineActuel() {
        DayOfWeek jour = LocalDate.now().getDayOfWeek();
        return switch (jour) {
            case MONDAY -> "LUNDI";
            case TUESDAY -> "MARDI";
            case WEDNESDAY -> "MERCREDI";
            case THURSDAY -> "JEUDI";
            case FRIDAY -> "VENDREDI";
            case SATURDAY -> "SAMEDI";
            case SUNDAY -> "DIMANCHE";
        };
    }

    private EvenementAcces journaliser(String personneId, String zoneId, String resultat, String raison, String capturePhoto) {
        EvenementAcces evt = new EvenementAcces();
        evt.setPersonneId(personneId);
        evt.setZoneId(zoneId);
        evt.setResultat(resultat);
        evt.setRaison(raison);
        evt.setCapturePhoto(capturePhoto);
        return evenementAccesRepository.save(evt);
    }

    private void creerAlerte(String type, String evenementId, String capturePhoto, List<Double> embedding) {
        Alerte alerte = new Alerte();
        alerte.setType(type);
        alerte.setEvenementId(evenementId);
        alerte.setCapturePhoto(capturePhoto);
        alerte.setEmbedding(embedding);
        alerteRepository.save(alerte);
    }
}