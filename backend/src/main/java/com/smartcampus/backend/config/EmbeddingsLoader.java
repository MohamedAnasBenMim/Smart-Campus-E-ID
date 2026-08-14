package com.smartcampus.backend.config;

import com.smartcampus.backend.model.Personne;
import com.smartcampus.backend.repository.PersonneRepository;
import com.smartcampus.backend.service.FaceServiceClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Recharge automatiquement tous les embeddings connus dans face-service
 * au démarrage du backend.
 *
 * POURQUOI CE FICHIER EXISTE : face-service garde les embeddings
 * UNIQUEMENT en mémoire (EMBEDDINGS_STORE, un simple dictionnaire
 * Python) — sans ce rechargement automatique, un simple redémarrage
 * de face-service rendrait toutes les personnes déjà enrôlées
 * méconnaissables, même si elles existent toujours dans MongoDB.
 *
 * IMPORTANT — ORDRE DE DÉMARRAGE : face-service doit déjà être
 * démarré et accessible AVANT de lancer le backend, sinon cet appel
 * échoue (avertissement journalisé, mais le backend démarre quand
 * même — ce n'est pas bloquant). Si l'avertissement apparaît,
 * redémarrez simplement le backend une fois face-service prêt.
 */
@Component
public class EmbeddingsLoader implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(EmbeddingsLoader.class);

    private final PersonneRepository personneRepository;
    private final FaceServiceClient faceServiceClient;

    public EmbeddingsLoader(PersonneRepository personneRepository, FaceServiceClient faceServiceClient) {
        this.personneRepository = personneRepository;
        this.faceServiceClient = faceServiceClient;
    }

    @Override
    public void run(ApplicationArguments args) {
        List<Personne> personnes = personneRepository.findAll();

        Map<String, List<Double>> embeddings = new HashMap<>();
        for (Personne p : personnes) {
            if (p.getEmbedding() != null && !p.getEmbedding().isEmpty()) {
                embeddings.put(p.getId(), p.getEmbedding());
            }
        }

        if (embeddings.isEmpty()) {
            log.info("[EmbeddingsLoader] Aucun embedding à recharger (aucune personne enrôlée pour l'instant).");
            return;
        }

        try {
            faceServiceClient.chargerEmbeddings(embeddings);
            log.info("[EmbeddingsLoader] {} embedding(s) rechargé(s) avec succès dans face-service.", embeddings.size());
        } catch (Exception e) {
            log.warn(
                "[EmbeddingsLoader] Impossible de recharger les embeddings dans face-service au démarrage : {}. " +
                "Vérifiez que face-service est bien démarré et accessible sur l'adresse configurée. " +
                "La reconnaissance ne fonctionnera pas tant que ce problème n'est pas résolu — " +
                "redémarrez le backend une fois face-service prêt.",
                e.getMessage()
            );
        }
    }
}