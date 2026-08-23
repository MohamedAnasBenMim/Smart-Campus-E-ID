package com.smartcampus.backend.controller;

import com.smartcampus.backend.model.Personne;
import com.smartcampus.backend.service.AlerteTraitementService;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

/**
 * Traitement spécialisé des alertes — au-delà du simple commentaire
 * (voir SupervisionController.traiterAlerte()), ces 4 actions
 * exploitent l'embedding conservé sur certaines alertes pour améliorer
 * la reconnaissance faciale, toujours avec validation humaine
 * explicite.
 */
@RestController
@RequestMapping("/api/alertes")
public class AlerteTraitementController {

    private final AlerteTraitementService service;

    public AlerteTraitementController(AlerteTraitementService service) {
        this.service = service;
    }

    /** IDENTITE_A_CONFIRMER — "oui, c'est bien elle" */
    @PostMapping("/{id}/confirmer-identite")
    public Map<String, String> confirmerIdentite(@PathVariable String id, Authentication authentication) {
        service.confirmerIdentite(id, authentication.getName());
        return Map.of("statut", "identité confirmée, profil mis à jour");
    }

    /** IDENTITE_A_CONFIRMER — "non, ce n'est pas elle" (avec correction optionnelle) */
    @PostMapping("/{id}/corriger-identite")
    public Map<String, String> corrigerIdentite(
            @PathVariable String id,
            @RequestBody(required = false) Map<String, String> body,
            Authentication authentication
    ) {
        String vraiePersonneId = body != null ? body.get("vraiePersonneId") : null;
        service.corrigerIdentite(id, vraiePersonneId, authentication.getName());
        return Map.of("statut", "identité corrigée");
    }

    /** ACCES_NON_AUTORISE — "je la reconnais, elle est déjà enrôlée" */
    @PostMapping("/{id}/associer-personne")
    public Map<String, String> associerPersonne(
            @PathVariable String id,
            @RequestBody Map<String, String> body,
            Authentication authentication
    ) {
        String personneId = body.get("personneId");
        if (personneId == null || personneId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "personneId requis");
        }
        service.associerPersonneExistante(id, personneId, authentication.getName());
        return Map.of("statut", "personne associée, profil mis à jour");
    }

    /** ACCES_NON_AUTORISE — "je la connais, mais elle n'est pas encore enrôlée" */
    @PostMapping("/{id}/enroler")
    public Personne enrolerDepuisAlerte(
            @PathVariable String id,
            @RequestBody Map<String, String> body,
            Authentication authentication
    ) {
        String nom = body.get("nom");
        String prenom = body.get("prenom");
        String role = body.getOrDefault("role", "ELEVE");

        if (nom == null || nom.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "nom requis");
        }

        return service.enrolerDepuisAlerte(id, nom, prenom, role, authentication.getName());
    }
}