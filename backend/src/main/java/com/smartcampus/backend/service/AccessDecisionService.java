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
 * AJOUT — capture photo : chaque alerte créée embarque désormais une
 * capture de l'image exacte qui l'a déclenchée (encodée en base64),
 * pour que le surveillant voie immédiatement de qui/quoi il s'agit,
 * sans avoir à retrouver le bon instant dans un flux vidéo.
 */
@Service
public class AccessDecisionService {

    private static final Logger log = LoggerFactory.getLogger(AccessDecisionService.class);

    private static final Set<String> RESULTATS_IGNORES = Set.of(
            "detection_incertaine", "angle_trop_marque"
    );

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

        // Capturée UNE SEULE FOIS ici, réutilisée pour toutes les alertes
        // éventuelles de cette frame — évite de relire le flux plusieurs fois.
        String capturePhoto = encoderImageEnBase64(image);

        for (FaceServiceResult.FaceResultItem face : result.getResultats()) {
            if (RESULTATS_IGNORES.contains(face.getResultat())) {
                continue;
            }

            if ("spoof_detecte".equals(face.getResultat())) {
                decisions.add(handleSpoof(zoneId, capturePhoto));
                continue;
            }

            if ("inconnu".equals(face.getResultat())) {
                decisions.add(handleInconnu(zoneId, capturePhoto));
                continue;
            }

            if ("reconnu".equals(face.getResultat())) {
                decisions.add(handleReconnu(face.getSubjectId(), zoneId, face.getAvertissement(), capturePhoto));
            }
        }

        if (result.isPresenceNonIdentifiee()) {
            decisions.add(handlePresenceNonIdentifiee(
                    zoneId, result.getPersonnesDetectees(), result.getVisagesDetectes(), capturePhoto
            ));
        }

        return decisions;
    }

    /**
     * Convertit l'image reçue en chaîne base64 prête à afficher directement
     * dans une balise <img> (préfixe data:...;base64, inclus). Ne fait
     * JAMAIS échouer la requête si la capture échoue — une alerte sans
     * photo reste préférable à aucune alerte du tout.
     */
    private String encoderImageEnBase64(MultipartFile image) {
        try {
            String typeContenu = image.getContentType() != null ? image.getContentType() : "image/jpeg";
            String base64 = Base64.getEncoder().encodeToString(image.getBytes());
            return "data:" + typeContenu + ";base64," + base64;
        } catch (IOException e) {
            log.warn("Échec de la capture photo pour une alerte : {}", e.getMessage());
            return null;
        }
    }

    private AccessDecision handleSpoof(String zoneId, String capturePhoto) {
        EvenementAcces evt = journaliser(null, zoneId, "REFUSE", "tentative de spoofing détectée");
        creerAlerte("SPOOFING", evt.getId(), capturePhoto);
        return new AccessDecision(null, null, zoneId, "REFUSE", evt.getRaison());
    }

    private AccessDecision handleInconnu(String zoneId, String capturePhoto) {
        EvenementAcces evt = journaliser(null, zoneId, "REFUSE", "personne non enrôlée");
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
        EvenementAcces evt = journaliser(null, zoneId, "REFUSE", raison);
        creerAlerte("PRESENCE_NON_IDENTIFIEE", evt.getId(), capturePhoto);
        return new AccessDecision(null, null, zoneId, "REFUSE", raison);
    }

    private AccessDecision handleReconnu(String personneId, String zoneId, String avertissement, String capturePhoto) {
        Optional<Personne> personneOpt = personneRepository.findById(personneId);
        if (personneOpt.isEmpty()) {
            return handleInconnu(zoneId, capturePhoto);
        }
        Personne personne = personneOpt.get();

        if (avertissement != null) {
            String raison = "identité probable (" + personne.getNom() + ") mais confiance réduite : " + avertissement;
            EvenementAcces evt = journaliser(personneId, zoneId, "REFUSE", raison);
            creerAlerte("IDENTITE_A_CONFIRMER", evt.getId(), capturePhoto);
            return new AccessDecision(personneId, personne.getNom(), zoneId, "REFUSE", raison);
        }

        Optional<RegleAcces> regleOpt = regleAccesRepository.findByPersonneIdAndZoneId(personneId, zoneId);
        if (regleOpt.isEmpty()) {
            EvenementAcces evt = journaliser(personneId, zoneId, "REFUSE", "zone non autorisée pour ce profil");
            creerAlerte("ACCES_INTERDIT", evt.getId(), capturePhoto);
            return new AccessDecision(personneId, personne.getNom(), zoneId, "REFUSE", evt.getRaison());
        }

        RegleAcces regle = regleOpt.get();
        LocalTime maintenant = LocalTime.now();
        boolean horaireValide = !maintenant.isBefore(regle.getHoraireDebut()) && !maintenant.isAfter(regle.getHoraireFin());

        if (!horaireValide) {
            EvenementAcces evt = journaliser(personneId, zoneId, "REFUSE", "hors horaire autorisé");
            creerAlerte("HORAIRE_INTERDIT", evt.getId(), capturePhoto);
            return new AccessDecision(personneId, personne.getNom(), zoneId, "REFUSE", evt.getRaison());
        }

        // Accès accordé : pas d'alerte, donc pas besoin de conserver la capture.
        EvenementAcces evt = journaliser(personneId, zoneId, "ACCORDE", "identité et règle d'accès validées");
        return new AccessDecision(personneId, personne.getNom(), zoneId, "ACCORDE", evt.getRaison());
    }

    private EvenementAcces journaliser(String personneId, String zoneId, String resultat, String raison) {
        EvenementAcces evt = new EvenementAcces();
        evt.setPersonneId(personneId);
        evt.setZoneId(zoneId);
        evt.setResultat(resultat);
        evt.setRaison(raison);
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