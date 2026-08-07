package com.smartcampus.backend.controller;

import com.smartcampus.backend.dto.UtilisateurRequest;
import com.smartcampus.backend.model.Utilisateur;
import com.smartcampus.backend.repository.UtilisateurRepository;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

/**
 * Gestion des comptes du dashboard (Admin/Surveillant) — réservé aux
 * administrateurs (@PreAuthorize). Ne concerne PAS les "Personne" (les
 * gens reconnus par les caméras) — voir PersonneController pour ça.
 */
@RestController
@RequestMapping("/api/utilisateurs")
@PreAuthorize("hasRole('ADMIN')")
public class UtilisateurController {

    private final UtilisateurRepository utilisateurRepository;
    private final PasswordEncoder passwordEncoder;

    public UtilisateurController(UtilisateurRepository utilisateurRepository, PasswordEncoder passwordEncoder) {
        this.utilisateurRepository = utilisateurRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @GetMapping
    public List<Utilisateur> lister() {
        return utilisateurRepository.findAll();
    }

    @PostMapping
    public Utilisateur creer(@Valid @RequestBody UtilisateurRequest request) {
        if (utilisateurRepository.findByEmail(request.getEmail()).isPresent()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Un compte existe déjà avec cet email");
        }

        Utilisateur utilisateur = new Utilisateur();
        utilisateur.setNom(request.getNom());
        utilisateur.setPrenom(request.getPrenom());
        utilisateur.setEmail(request.getEmail());
        utilisateur.setMotDePasseHache(passwordEncoder.encode(request.getMotDePasse()));
        utilisateur.setRole(request.getRole());

        return utilisateurRepository.save(utilisateur);
    }

    @PutMapping("/{id}")
    public Utilisateur modifier(@PathVariable String id, @RequestBody Utilisateur modifications) {
        Utilisateur utilisateur = utilisateurRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Compte introuvable"));

        if (modifications.getNom() != null) utilisateur.setNom(modifications.getNom());
        if (modifications.getPrenom() != null) utilisateur.setPrenom(modifications.getPrenom());
        if (modifications.getStatut() != null) utilisateur.setStatut(modifications.getStatut());

        return utilisateurRepository.save(utilisateur);
    }

    @DeleteMapping("/{id}")
    public void supprimer(@PathVariable String id) {
        utilisateurRepository.deleteById(id);
    }
}