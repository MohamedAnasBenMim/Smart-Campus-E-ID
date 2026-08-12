package com.smartcampus.backend.controller;

import com.smartcampus.backend.model.Alerte;
import com.smartcampus.backend.model.EvenementAcces;
import com.smartcampus.backend.repository.AlerteRepository;
import com.smartcampus.backend.repository.EvenementAccesRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@RestController
public class SupervisionController {

    private final AlerteRepository alerteRepository;
    private final EvenementAccesRepository evenementAccesRepository;

    public SupervisionController(AlerteRepository alerteRepository, EvenementAccesRepository evenementAccesRepository) {
        this.alerteRepository = alerteRepository;
        this.evenementAccesRepository = evenementAccesRepository;
    }

    @GetMapping("/api/alertes")
    public List<Alerte> listerAlertes() {
        return alerteRepository.findAll();
    }

    /**
     * Marquer une alerte comme traitée — enregistre désormais QUI (déduit du
     * token JWT), COMMENT (commentaire libre fourni par l'admin/surveillant)
     * et QUAND (automatique), pas seulement le statut.
     */
    @PatchMapping("/api/alertes/{id}")
    public Alerte traiterAlerte(
            @PathVariable String id,
            @RequestBody Map<String, String> body,
            Authentication authentication
    ) {
        Alerte alerte = alerteRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Alerte introuvable"));

        String nouveauStatut = body.getOrDefault("statut", "TRAITEE");
        alerte.setStatut(nouveauStatut);

        if (body.get("commentaireTraitement") != null) {
            alerte.setCommentaireTraitement(body.get("commentaireTraitement"));
        }

        if ("TRAITEE".equals(nouveauStatut)) {
            alerte.setDateTraitement(Instant.now());
            if (authentication != null) {
                alerte.setTraitePar(authentication.getName()); // email, extrait du JWT
            }
        }

        return alerteRepository.save(alerte);
    }

    @GetMapping("/api/access-events")
    public List<EvenementAcces> listerEvenements() {
        return evenementAccesRepository.findAll();
    }
}