package com.smartcampus.backend.service;

import com.smartcampus.backend.dto.AccessDecision;
import com.smartcampus.backend.dto.FaceServiceResult;
import com.smartcampus.backend.model.Alerte;
import com.smartcampus.backend.model.EvenementAcces;
import com.smartcampus.backend.model.Personne;
import com.smartcampus.backend.model.RegleAcces;
import com.smartcampus.backend.repository.AlerteRepository;
import com.smartcampus.backend.repository.EvenementAccesRepository;
import com.smartcampus.backend.repository.PersonneRepository;
import com.smartcampus.backend.repository.RegleAccesRepository;
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
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * BF-08 / BF-09 — Reçoit une frame + une zone, appelle le service de
 * reconnaissance, croise le résultat avec les règles d'accès, décide,
 * puis journalise systématiquement.
 *
 * NOUVEAU : chaque capture est désormais ANNOTÉE — un cadre est dessiné
 * autour du visage précis concerné par la décision (rouge pour un
 * problème, vert pour un accès accordé). Utile quand plusieurs personnes
 * sont présentes sur la même frame : on sait immédiatement laquelle a
 * déclenché l'alerte, sans avoir à deviner.
 */
@Service
public class AccessDecisionService {

    private static final Logger log = LoggerFactory.getLogger(AccessDecisionService.class);

    private static final Set<String> RESULTATS_IGNORES = Set.of(
            "detection_incertaine", "angle_trop_marque"
    );

    private static final Color COULEUR_PROBLEME = new Color(214, 69, 80);   // rouge — cohérent avec le dashboard
    private static final Color COULEUR_ACCORDE = new Color(14, 143, 107);   // vert — cohérent avec le dashboard

    private final FaceServiceClient faceServiceClient;
    private final PersonneRepository personneRepository;
    private final RegleAccesRepository regleAccesRepository;
    private final EvenementAccesRepository evenementAccesRepository;
    private final AlerteRepository alerteRepository;

    public AccessDecisionService(
            FaceServiceClient faceServiceClient,
            PersonneRepository personneRepository,
            RegleAccesRepository regleAccesRepository,
            EvenementAccesRepository evenementAccesRepository,
            AlerteRepository alerteRepository
    ) {
        this.faceServiceClient = faceServiceClient;
        this.personneRepository = personneRepository;
        this.regleAccesRepository = regleAccesRepository;
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
                decisions.add(handleInconnu(zoneId, capture));
                continue;
            }

            if ("reconnu".equals(face.getResultat())) {
                decisions.add(handleReconnu(
                        face.getSubjectId(), zoneId, face.getAvertissement(),
                        imageBytesOriginaux, typeContenu, face.getBbox()
                ));
            }
        }

        if (result.isPresenceNonIdentifiee()) {
            // Pas de bbox précis possible ici, par nature du cas : on ne
            // sait justement pas identifier quel visage pose problème.
            String capture = "data:" + typeContenu + ";base64," + Base64.getEncoder().encodeToString(imageBytesOriginaux);
            decisions.add(handlePresenceNonIdentifiee(
                    zoneId, result.getPersonnesDetectees(), result.getVisagesDetectes(), capture
            ));
        }

        return decisions;
    }

    /**
     * Dessine un cadre coloré (avec étiquette) autour d'un visage précis
     * dans l'image, puis encode le résultat en base64.
     *
     * Ne fait JAMAIS échouer la requête : en cas de souci (bbox absente,
     * image illisible...), renvoie l'image originale non annotée plutôt
     * que de bloquer la journalisation.
     */
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
        EvenementAcces evt = journaliser(null, zoneId, "REFUSE", "tentative de spoofing détectée", capturePhoto);
        creerAlerte("SPOOFING", evt.getId(), capturePhoto);
        return new AccessDecision(null, null, zoneId, "REFUSE", evt.getRaison());
    }

    private AccessDecision handleInconnu(String zoneId, String capturePhoto) {
        EvenementAcces evt = journaliser(null, zoneId, "REFUSE", "personne non enrôlée", capturePhoto);
        creerAlerte("ACCES_NON_AUTORISE", evt.getId(), capturePhoto);
        return new AccessDecision(null, null, zoneId, "REFUSE", evt.getRaison());
    }

    private AccessDecision handlePresenceNonIdentifiee(
            String zoneId, int personnesDetectees, int visagesDetectes, String capturePhoto
    ) {
        String raison = String.format(
                "%d personne(s) détectée(s) mais identité confirmée pour %d visage(s) seulement — présence non identifiée",
                personnesDetectees, visagesDetectes
        );
        EvenementAcces evt = journaliser(null, zoneId, "REFUSE", raison, capturePhoto);
        creerAlerte("PRESENCE_NON_IDENTIFIEE", evt.getId(), capturePhoto);
        return new AccessDecision(null, null, zoneId, "REFUSE", raison);
    }

    private AccessDecision handleReconnu(
            String personneId, String zoneId, String avertissement,
            byte[] imageBytesOriginaux, String typeContenu, List<Integer> bbox
    ) {
        Optional<Personne> personneOpt = personneRepository.findById(personneId);
        if (personneOpt.isEmpty()) {
            String capture = annoterImage(imageBytesOriginaux, typeContenu, bbox, "INCONNU", COULEUR_PROBLEME);
            return handleInconnu(zoneId, capture);
        }
        Personne personne = personneOpt.get();

        if (avertissement != null) {
            String raison = "identité probable (" + personne.getNom() + ") mais confiance réduite : " + avertissement;
            String capture = annoterImage(imageBytesOriginaux, typeContenu, bbox, "À CONFIRMER", COULEUR_PROBLEME);
            EvenementAcces evt = journaliser(personneId, zoneId, "REFUSE", raison, capture);
            creerAlerte("IDENTITE_A_CONFIRMER", evt.getId(), capture);
            return new AccessDecision(personneId, personne.getNom(), zoneId, "REFUSE", raison);
        }

        Optional<RegleAcces> regleOpt = regleAccesRepository.findByPersonneIdAndZoneId(personneId, zoneId);
        if (regleOpt.isEmpty()) {
            String capture = annoterImage(imageBytesOriginaux, typeContenu, bbox, personne.getNom() + " — ZONE INTERDITE", COULEUR_PROBLEME);
            EvenementAcces evt = journaliser(personneId, zoneId, "REFUSE", "zone non autorisée pour ce profil", capture);
            creerAlerte("ACCES_INTERDIT", evt.getId(), capture);
            return new AccessDecision(personneId, personne.getNom(), zoneId, "REFUSE", evt.getRaison());
        }

        RegleAcces regle = regleOpt.get();
        LocalTime maintenant = LocalTime.now();
        boolean horaireValide = !maintenant.isBefore(regle.getHoraireDebut()) && !maintenant.isAfter(regle.getHoraireFin());

        if (!horaireValide) {
            String capture = annoterImage(imageBytesOriginaux, typeContenu, bbox, personne.getNom() + " — HORS HORAIRE", COULEUR_PROBLEME);
            EvenementAcces evt = journaliser(personneId, zoneId, "REFUSE", "hors horaire autorisé", capture);
            creerAlerte("HORAIRE_INTERDIT", evt.getId(), capture);
            return new AccessDecision(personneId, personne.getNom(), zoneId, "REFUSE", evt.getRaison());
        }

        // Accès accordé — cadre VERT avec le nom, pour la présence.
        String capture = annoterImage(imageBytesOriginaux, typeContenu, bbox, personne.getNom(), COULEUR_ACCORDE);
        EvenementAcces evt = journaliser(personneId, zoneId, "ACCORDE", "identité et règle d'accès validées", capture);
        return new AccessDecision(personneId, personne.getNom(), zoneId, "ACCORDE", evt.getRaison());
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

    private void creerAlerte(String type, String evenementId, String capturePhoto) {
        Alerte alerte = new Alerte();
        alerte.setType(type);
        alerte.setEvenementId(evenementId);
        alerte.setCapturePhoto(capturePhoto);
        alerteRepository.save(alerte);
    }
}