package com.smartcampus.backend.controller;

import com.smartcampus.backend.model.Zone;
import com.smartcampus.backend.repository.ZoneRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
@RequestMapping("/api/zones")
public class ZoneController {

    private final ZoneRepository zoneRepository;

    public ZoneController(ZoneRepository zoneRepository) {
        this.zoneRepository = zoneRepository;
    }

    @GetMapping
    public List<Zone> lister() {
        return zoneRepository.findAll();
    }

    @PreAuthorize("hasRole('ADMIN')")
    @PostMapping
    public Zone creer(@RequestBody Zone zone) {
        return zoneRepository.save(zone);
    }

    @PreAuthorize("hasRole('ADMIN')")
    @PutMapping("/{id}")
    public Zone modifier(@PathVariable String id, @RequestBody Zone modifications) {
        Zone zone = zoneRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Zone introuvable"));

        zone.setNom(modifications.getNom());
        zone.setDescription(modifications.getDescription());

        return zoneRepository.save(zone);
    }

    @PreAuthorize("hasRole('ADMIN')")
    @DeleteMapping("/{id}")
    public void supprimer(@PathVariable String id) {
        zoneRepository.deleteById(id);
    }
}