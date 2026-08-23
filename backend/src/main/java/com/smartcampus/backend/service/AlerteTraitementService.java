package com.smartcampus.backend.service;

import com.smartcampus.backend.model.Alerte;
import com.smartcampus.backend.model.EvenementAcces;
import com.smartcampus.backend.model.Personne;
import com.smartcampus.backend.repository.AlerteRepository;
import com.smartcampus.backend.repository.EvenementAccesRepository;
import com.smartcampus.backend.repository.PersonneRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Traitement SPÉCIALISÉ des alertes — au-delà du simple commentaire
 * libre (déjà géré par SupervisionController.traiterAlerte()), ce
 * service permet d'utiliser l'embedding conservé sur certaines alertes
 * pour AMÉLIORER LA RECONNAISSANCE, avec l'humain qui reste toujours
 * la seule source de vérité :
 *
 *   - IDENTITE_A_CONFIRMER : confirmer (améliore le profil proposé) ou
 *     corriger (réassocie à la bonne personne, ou ne fait rien si
 *     inconnue).
 *   - ACCES_NON_AUTORISE : associer à une personne déjà enrôlée, ou
 *     enrôler une toute nouvelle personne, à partir de l'embedding
 *     déjà capturé sur l'alerte.
 *
 * IMPORTANT : à chaque mise à jour de profil, MongoDB ET face-service
 * sont synchronisés dans la foulée (voir rechargerFaceService()) — un
 * profil mis à jour en base mais jamais renvoyé à face-service
 * continuerait, silencieusement, à être mal reconnu jusqu'au prochain
 * redémarrage du backend.
 */
@Service
public class AlerteTraitementService {

    private static final Logger log = LoggerFactory.getLogger(AlerteTraitementService.class);

    private final AlerteRepository alerteRepository;
    private final EvenementAccesRepository evenementAccesRepository;
    private final PersonneRepository personneRepository;
    private final FaceServiceClient faceServiceClient;

    public AlerteTraitementService(
            AlerteRepository alerteRepository,
            EvenementAccesRepository evenementAccesRepository,
            PersonneRepository personneRepository,
            FaceServiceClient faceServiceClient
    ) {
        this.alerteRepository = alerteRepository;
        this.evenementAccesRepository = evenementAccesRepository;
        this.personneRepository = personneRepository;
        this.faceServiceClient = faceServiceClient;
    }

    /**
     * L'admin confirme que l'identité proposée par le système était la
     * bonne — l'embedding de l'alerte est intégré au profil de cette
     * personne (améliore sa reconnaissance future).
     */
    public void confirmerIdentite(String alerteId, String traitePar) {
        Alerte alerte = recupererAlerte(alerteId);
        verifierType(alerte, "IDENTITE_A_CONFIRMER");

        EvenementAcces evt = evenementAccesRepository.findById(alerte.getEvenementId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Événement introuvable"));

        if (evt.getPersonneId() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Aucune personne associée à cet événement");
        }

        mettreAJourProfil(evt.getPersonneId(), alerte.getEmbedding());
        marquerTraitee(alerte, traitePar, "Identité confirmée par l'administrateur — profil mis à jour");
    }

    /**
     * L'admin indique que l'identité proposée était FAUSSE.
     *
     * Si vraiePersonneId est fourni : l'embedding est réassocié à la
     * bonne personne à la place. Sinon : l'alerte est simplement
     * marquée traitée, SANS mise à jour de profil — le système ne
     * touche jamais un profil sur la base d'une supposition.
     */
    public void corrigerIdentite(String alerteId, String vraiePersonneId, String traitePar) {
        Alerte alerte = recupererAlerte(alerteId);
        verifierType(alerte, "IDENTITE_A_CONFIRMER");

        String commentaire;
        if (vraiePersonneId != null && !vraiePersonneId.isBlank()) {
            mettreAJourProfil(vraiePersonneId, alerte.getEmbedding());
            commentaire = "Identité corrigée par l'administrateur — embedding réassocié à la bonne personne";
        } else {
            commentaire = "Identité invalidée par l'administrateur — aucune correction automatique appliquée (vraie identité inconnue)";
        }

        marquerTraitee(alerte, traitePar, commentaire);
    }

    /**
     * L'admin reconnaît visuellement une personne INCONNUE comme étant
     * déjà enrôlée sous un autre profil — associe l'embedding à ce
     * profil existant.
     */
    public void associerPersonneExistante(String alerteId, String personneId, String traitePar) {
        Alerte alerte = recupererAlerte(alerteId);
        verifierType(alerte, "ACCES_NON_AUTORISE");

        mettreAJourProfil(personneId, alerte.getEmbedding());
        marquerTraitee(alerte, traitePar, "Personne identifiée manuellement par l'administrateur — profil mis à jour");
    }

    /**
     * L'admin reconnaît une personne INCONNUE mais pas encore enrôlée —
     * crée un nouveau profil directement avec l'embedding de l'alerte,
     * pas besoin de nouvelles photos.
     */
    public Personne enrolerDepuisAlerte(String alerteId, String nom, String prenom, String role, String traitePar) {
        Alerte alerte = recupererAlerte(alerteId);
        verifierType(alerte, "ACCES_NON_AUTORISE");

        if (alerte.getEmbedding() == null || alerte.getEmbedding().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Aucun embedding disponible sur cette alerte");
        }

        Personne personne = new Personne();
        personne.setNom(nom);
        personne.setPrenom(prenom);
        personne.setRole(role);
        personne.setStatut("ACTIF");
        personne.setEmbedding(alerte.getEmbedding());
        Personne enregistree = personneRepository.save(personne);

        rechargerFaceService();
        marquerTraitee(alerte, traitePar, "Personne enrôlée depuis cette alerte : " + nom + (prenom != null ? " " + prenom : ""));

        return enregistree;
    }

    /**
     * Met à jour le profil d'une personne avec un nouvel embedding.
     *
     * Même principe que embedding_candidates.py côté Python (moyenne
     * simple) — mais appliqué ici directement, immédiatement, car
     * l'action vient d'une VALIDATION HUMAINE EXPLICITE (contrairement
     * aux candidats automatiques, qui attendent une validation
     * ultérieure avant d'être appliqués).
     */
    private void mettreAJourProfil(String personneId, List<Double> nouvelEmbedding) {
        if (nouvelEmbedding == null || nouvelEmbedding.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Aucun embedding disponible sur cette alerte");
        }

        Personne personne = personneRepository.findById(personneId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Personne introuvable"));

        List<Double> ancienEmbedding = personne.getEmbedding();
        List<Double> embeddingFinal;

        if (ancienEmbedding == null || ancienEmbedding.isEmpty() || ancienEmbedding.size() != nouvelEmbedding.size()) {
            embeddingFinal = nouvelEmbedding;
        } else {
            embeddingFinal = new ArrayList<>(ancienEmbedding.size());
            for (int i = 0; i < ancienEmbedding.size(); i++) {
                embeddingFinal.add((ancienEmbedding.get(i) + nouvelEmbedding.get(i)) / 2.0);
            }
        }

        personne.setEmbedding(embeddingFinal);
        personneRepository.save(personne);
        rechargerFaceService();

        log.info(
                "[ALERTE-TRAITEMENT] Profil {} mis à jour ({})",
                personneId,
                (ancienEmbedding == null || ancienEmbedding.isEmpty()) ? "aucun profil existant, embedding initial" : "moyenne avec le profil existant"
        );
    }

    /**
     * Renvoie TOUS les embeddings à jour à face-service — pas seulement
     * celui qui vient de changer, pour rester cohérent avec la logique
     * déjà utilisée par EmbeddingsLoader au démarrage.
     *
     * N'échoue JAMAIS l'opération globale : MongoDB reste la source de
     * vérité même si face-service est temporairement injoignable.
     */
    private void rechargerFaceService() {
        try {
            Map<String, List<Double>> tousLesEmbeddings = new HashMap<>();
            for (Personne p : personneRepository.findAll()) {
                if (p.getEmbedding() != null && !p.getEmbedding().isEmpty()) {
                    tousLesEmbeddings.put(p.getId(), p.getEmbedding());
                }
            }
            faceServiceClient.chargerEmbeddings(tousLesEmbeddings);
        } catch (Exception e) {
            log.warn(
                    "[ALERTE-TRAITEMENT] Échec du rechargement dans face-service : {} — MongoDB est à jour, "
                            + "mais face-service utilisera l'ancienne version jusqu'au prochain redémarrage du backend.",
                    e.getMessage()
            );
        }
    }

    private Alerte recupererAlerte(String alerteId) {
        return alerteRepository.findById(alerteId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Alerte introuvable"));
    }

    private void verifierType(Alerte alerte, String typeAttendu) {
        if (!typeAttendu.equals(alerte.getType())) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Cette action n'est valide que pour les alertes de type " + typeAttendu
            );
        }
    }

    private void marquerTraitee(Alerte alerte, String traitePar, String commentaire) {
        alerte.setStatut("TRAITEE");
        alerte.setCommentaireTraitement(commentaire);
        alerte.setTraitePar(traitePar);
        alerte.setDateTraitement(Instant.now());
        alerteRepository.save(alerte);
    }
}