package com.smartcampus.backend.controller;

import com.smartcampus.backend.dto.RegleAccesRoleLotRequest;
import com.smartcampus.backend.model.RegleAccesRole;
import com.smartcampus.backend.repository.RegleAccesRoleRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.List;

@RestController
@RequestMapping("/api/regles-role")
public class RegleAccesRoleController {

    private final RegleAccesRoleRepository repository;

    public RegleAccesRoleController(RegleAccesRoleRepository repository) {
        this.repository = repository;
    }

    @GetMapping
    public List<RegleAccesRole> lister() {
        return repository.findAll();
    }

    @PreAuthorize("hasRole('ADMIN')")
    @PostMapping
    public RegleAccesRole creer(@RequestBody RegleAccesRole regle) {
        return repository.save(regle);
    }

    /**
     * NOUVEAU — création GROUPÉE : un rôle, plusieurs zones
     * sélectionnées d'un coup, un seul horaire pour toutes. Évite de
     * répéter la même action pour chaque salle une par une.
     */
    @PreAuthorize("hasRole('ADMIN')")
    @PostMapping("/lot")
    public List<RegleAccesRole> creerEnLot(@RequestBody RegleAccesRoleLotRequest requete) {
        List<RegleAccesRole> creees = new ArrayList<>();

        for (String zoneId : requete.getZoneIds()) {
            RegleAccesRole regle = new RegleAccesRole();
            regle.setRole(requete.getRole());
            regle.setZoneId(zoneId);
            regle.setHoraireDebut(requete.getHoraireDebut());
            regle.setHoraireFin(requete.getHoraireFin());
            creees.add(repository.save(regle));
        }

        return creees;
    }

    @PreAuthorize("hasRole('ADMIN')")
    @PutMapping("/{id}")
    public RegleAccesRole modifier(@PathVariable String id, @RequestBody RegleAccesRole modifications) {
        RegleAccesRole regle = repository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Règle introuvable"));

        regle.setRole(modifications.getRole());
        regle.setZoneId(modifications.getZoneId());
        regle.setHoraireDebut(modifications.getHoraireDebut());
        regle.setHoraireFin(modifications.getHoraireFin());

        return repository.save(regle);
    }

    @PreAuthorize("hasRole('ADMIN')")
    @DeleteMapping("/{id}")
    public void supprimer(@PathVariable String id) {
        repository.deleteById(id);
    }
}