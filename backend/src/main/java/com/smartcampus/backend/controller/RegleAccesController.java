package com.smartcampus.backend.controller;

import com.smartcampus.backend.dto.RegleAccesRequest;
import com.smartcampus.backend.model.RegleAcces;
import com.smartcampus.backend.repository.RegleAccesRepository;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.time.LocalTime;
import java.util.List;

@RestController
@RequestMapping("/api/regles")
public class RegleAccesController {

    private final RegleAccesRepository regleAccesRepository;

    public RegleAccesController(RegleAccesRepository regleAccesRepository) {
        this.regleAccesRepository = regleAccesRepository;
    }

    @GetMapping
    public List<RegleAcces> lister() {
        return regleAccesRepository.findAll();
    }

    @PreAuthorize("hasRole('ADMIN')")
    @PostMapping
    public RegleAcces creer(@Valid @RequestBody RegleAccesRequest request) {
        RegleAcces regle = new RegleAcces();
        regle.setPersonneId(request.getPersonneId());
        regle.setZoneId(request.getZoneId());
        regle.setHoraireDebut(LocalTime.parse(request.getHoraireDebut()));
        regle.setHoraireFin(LocalTime.parse(request.getHoraireFin()));
        return regleAccesRepository.save(regle);
    }

    @PreAuthorize("hasRole('ADMIN')")
    @DeleteMapping("/{id}")
    public void supprimer(@PathVariable String id) {
        regleAccesRepository.deleteById(id);
    }
}