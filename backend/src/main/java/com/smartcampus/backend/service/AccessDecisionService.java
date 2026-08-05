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

@Service
public class AccessDecisionService {

    private static final Set<String> RESULTATS_IGNORES = Set.of(
            "detection_incertaine", "angle_trop_marque", "visage_trop_petit"
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
                continue; // détection trop incertaine, on n'en fait rien
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
                decisions.add(handleReconnu(face.getSubjectId(), zoneId));
            }
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

    private AccessDecision handleReconnu(String personneId, String zoneId) {
        Optional<Personne> personneOpt = personneRepository.findById(personneId);
        if (personneOpt.isEmpty()) {
            // Cas limite : reconnu par le service IA mais absent de notre base
            // (désynchronisation cache Python / MongoDB) — traité comme inconnu.
            return handleInconnu(zoneId);
        }
        Personne personne = personneOpt.get();

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
