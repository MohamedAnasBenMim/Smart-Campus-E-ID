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
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * BF-08 / BF-09 — Reçoit une frame + une zone, appelle le service de
 * reconnaissance, croise le résultat avec les règles d'accès, décide,
 * puis journalise systématiquement.
 *
 * AJOUT IMPORTANT : gère maintenant le cas "présence détectée sans visage
 * exploitable" (ex. personne de dos) — auparavant, ce cas ne générait
 * AUCUN événement ni alerte, un vrai angle mort de sécurité identifié
 * lors des tests. Le service Python détecte la silhouette (HOG) même sans
 * visage visible ; ce service traduit ça en une alerte concrète.
 */
@Service
public class AccessDecisionService {

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

        for (FaceServiceResult.FaceResultItem face : result.getResultats()) {
            if (RESULTATS_IGNORES.contains(face.getResultat())) {
                continue;
            }

            if ("spoof_detecte".equals(face.getResultat())) {
                decisions.add(handleSpoof(zoneId));
                continue;
            }

            if ("inconnu".equals(face.getResultat())) {
                decisions.add(handleInconnu(zoneId));
                continue;
            }

            if ("reconnu".equals(face.getResultat())) {
                decisions.add(handleReconnu(face.getSubjectId(), zoneId, face.getAvertissement()));
            }
        }

        // NOUVEAU : silhouette détectée sans visage exploitable pour l'identifier
        // (personne de dos, visage masqué...). Avant cet ajout, ce cas ne
        // générait aucun événement ni alerte — un vrai trou de sécurité.
        if (result.isPresenceNonIdentifiee()) {
            decisions.add(handlePresenceNonIdentifiee(zoneId, result.getPersonnesDetectees(), result.getVisagesDetectes()));
        }

        return decisions;
    }

    private AccessDecision handleSpoof(String zoneId) {
        EvenementAcces evt = journaliser(null, zoneId, "REFUSE", "tentative de spoofing détectée");
        creerAlerte("SPOOFING", evt.getId());
        return new AccessDecision(null, null, zoneId, "REFUSE", evt.getRaison());
    }

    private AccessDecision handleInconnu(String zoneId) {
        EvenementAcces evt = journaliser(null, zoneId, "REFUSE", "personne non enrôlée");
        creerAlerte("ACCES_NON_AUTORISE", evt.getId());
        return new AccessDecision(null, null, zoneId, "REFUSE", evt.getRaison());
    }

    /**
     * NOUVEAU — cas "présence détectée, identité inconnue" : quelqu'un a été
     * repéré (silhouette) mais aucun visage n'a pu confirmer qui, ni même
     * tenter la reconnaissance. Traité comme un refus + alerte, exactement
     * comme "inconnu", pour ne jamais laisser ce cas silencieux.
     */
    private AccessDecision handlePresenceNonIdentifiee(String zoneId, int personnesDetectees, int visagesDetectes) {
        String raison = String.format(
                "%d personne(s) détectée(s) mais identité confirmée pour %d visage(s) seulement — présence non identifiée",
                personnesDetectees, visagesDetectes
        );
        EvenementAcces evt = journaliser(null, zoneId, "REFUSE", raison);
        creerAlerte("PRESENCE_NON_IDENTIFIEE", evt.getId());
        return new AccessDecision(null, null, zoneId, "REFUSE", raison);
    }

    private AccessDecision handleReconnu(String personneId, String zoneId, String avertissement) {
        Optional<Personne> personneOpt = personneRepository.findById(personneId);
        if (personneOpt.isEmpty()) {
            return handleInconnu(zoneId);
        }
        Personne personne = personneOpt.get();

        // NOUVEAU : une correspondance sur un visage à fiabilité réduite (ex. trop
        // petit — rappel : ~78% de précision à 15px contre ~98% à 45px) n'accorde
        // JAMAIS l'accès automatiquement, même si la règle zone/horaire serait valide.
        // On préfère une vérification humaine à un accès basé sur une identité
        // statistiquement incertaine. L'identité probable reste indiquée, pour aider
        // le surveillant, mais le statut est REFUSE.
        if (avertissement != null) {
            String raison = "identité probable (" + personne.getNom() + ") mais confiance réduite : " + avertissement;
            EvenementAcces evt = journaliser(personneId, zoneId, "REFUSE", raison);
            creerAlerte("IDENTITE_A_CONFIRMER", evt.getId());
            return new AccessDecision(personneId, personne.getNom(), zoneId, "REFUSE", raison);
        }

        Optional<RegleAcces> regleOpt = regleAccesRepository.findByPersonneIdAndZoneId(personneId, zoneId);
        if (regleOpt.isEmpty()) {
            EvenementAcces evt = journaliser(personneId, zoneId, "REFUSE", "zone non autorisée pour ce profil");
            creerAlerte("ACCES_INTERDIT", evt.getId());
            return new AccessDecision(personneId, personne.getNom(), zoneId, "REFUSE", evt.getRaison());
        }

        RegleAcces regle = regleOpt.get();
        LocalTime maintenant = LocalTime.now();
        boolean horaireValide = !maintenant.isBefore(regle.getHoraireDebut()) && !maintenant.isAfter(regle.getHoraireFin());

        if (!horaireValide) {
            EvenementAcces evt = journaliser(personneId, zoneId, "REFUSE", "hors horaire autorisé");
            creerAlerte("HORAIRE_INTERDIT", evt.getId());
            return new AccessDecision(personneId, personne.getNom(), zoneId, "REFUSE", evt.getRaison());
        }

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

    private void creerAlerte(String type, String evenementId) {
        Alerte alerte = new Alerte();
        alerte.setType(type);
        alerte.setEvenementId(evenementId);
        alerteRepository.save(alerte);
    }
}