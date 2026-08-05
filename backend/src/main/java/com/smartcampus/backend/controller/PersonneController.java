package com.smartcampus.backend.controller;

import com.smartcampus.backend.model.Personne;
import com.smartcampus.backend.repository.PersonneRepository;
import com.smartcampus.backend.service.FaceServiceClient;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.util.List;

@RestController
@RequestMapping("/api/personnes")
public class PersonneController {

    private final PersonneRepository personneRepository;
    private final FaceServiceClient faceServiceClient;

    public PersonneController(PersonneRepository personneRepository, FaceServiceClient faceServiceClient) {
        this.personneRepository = personneRepository;
        this.faceServiceClient = faceServiceClient;
    }

    @GetMapping
    public List<Personne> lister() {
        return personneRepository.findAll();
    }

    @GetMapping("/{id}")
    public Personne consulter(@PathVariable String id) {
        return personneRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Personne introuvable"));
    }

    /**
     * BF-01 / BF-02 — Crée un profil : enregistre nom/rôle, ET déclenche
     * l'appel au service Python pour calculer l'embedding à partir des photos.
     */
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Personne creer(
            @RequestParam String nom,
            @RequestParam String role,
            @RequestParam("images") List<MultipartFile> images
    ) throws IOException {
        Personne personne = new Personne();
        personne.setNom(nom);
        personne.setRole(role);
        // Sauvegarde d'abord pour obtenir un id, utilisé comme subject_id côté service IA
        personne = personneRepository.save(personne);

        List<Double> embedding = faceServiceClient.enroll(personne.getId(), images);
        personne.setEmbedding(embedding);
        return personneRepository.save(personne);
    }

    /** BF-04 — Modifier le rôle ou le statut (actif/inactif) d'un profil. */
    @PutMapping("/{id}")
    public Personne modifier(@PathVariable String id, @RequestBody Personne modifications) {
        Personne personne = personneRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Personne introuvable"));
        if (modifications.getNom() != null) personne.setNom(modifications.getNom());
        if (modifications.getRole() != null) personne.setRole(modifications.getRole());
        if (modifications.getStatut() != null) personne.setStatut(modifications.getStatut());
        return personneRepository.save(personne);
    }

    /** BF-04 — Suppression d'un profil. */
    @DeleteMapping("/{id}")
    public void supprimer(@PathVariable String id) {
        personneRepository.deleteById(id);
    }
}
