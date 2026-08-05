package com.smartcampus.backend.controller;

import com.smartcampus.backend.model.Alerte;
import com.smartcampus.backend.model.EvenementAcces;
import com.smartcampus.backend.repository.AlerteRepository;
import com.smartcampus.backend.repository.EvenementAccesRepository;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

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

    /** Marquer une alerte comme traitée par le surveillant. */
    @PatchMapping("/api/alertes/{id}")
    public Alerte traiterAlerte(@PathVariable String id, @RequestBody Map<String, String> body) {
        Alerte alerte = alerteRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Alerte introuvable"));
        alerte.setStatut(body.getOrDefault("statut", "TRAITEE"));
        return alerteRepository.save(alerte);
    }

    @GetMapping("/api/access-events")
    public List<EvenementAcces> listerEvenements() {
        return evenementAccesRepository.findAll();
    }
}
