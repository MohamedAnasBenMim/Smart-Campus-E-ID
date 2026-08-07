package com.smartcampus.backend.controller;

import com.smartcampus.backend.dto.LoginRequest;
import com.smartcampus.backend.dto.LoginResponse;
import com.smartcampus.backend.model.Utilisateur;
import com.smartcampus.backend.repository.UtilisateurRepository;
import com.smartcampus.backend.service.JwtService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.Optional;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UtilisateurRepository utilisateurRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public AuthController(UtilisateurRepository utilisateurRepository, PasswordEncoder passwordEncoder, JwtService jwtService) {
        this.utilisateurRepository = utilisateurRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    @PostMapping("/login")
    public LoginResponse login(@Valid @RequestBody LoginRequest request) {
        Optional<Utilisateur> utilisateurOpt = utilisateurRepository.findByEmail(request.getEmail());

        if (utilisateurOpt.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Email ou mot de passe incorrect");
        }

        Utilisateur utilisateur = utilisateurOpt.get();

        if (!"ACTIF".equals(utilisateur.getStatut())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Ce compte est désactivé");
        }

        if (!passwordEncoder.matches(request.getMotDePasse(), utilisateur.getMotDePasseHache())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Email ou mot de passe incorrect");
        }

        String token = jwtService.generateToken(utilisateur.getEmail(), utilisateur.getRole());
        return new LoginResponse(token, utilisateur.getNom(), utilisateur.getPrenom(), utilisateur.getRole());
    }

    // NOTE : "mot de passe oublié" volontairement pas encore implémenté ici —
    // nécessite l'envoi d'email (SMTP), une intégration séparée qu'on
    // ajoutera une fois l'authentification de base validée.
}