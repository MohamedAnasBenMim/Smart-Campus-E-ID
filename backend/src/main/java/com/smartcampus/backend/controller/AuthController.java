package com.smartcampus.backend.controller;

import com.smartcampus.backend.dto.ForgotPasswordRequest;
import com.smartcampus.backend.dto.LoginRequest;
import com.smartcampus.backend.dto.LoginResponse;
import com.smartcampus.backend.dto.ResetPasswordRequest;
import com.smartcampus.backend.model.Utilisateur;
import com.smartcampus.backend.repository.UtilisateurRepository;
import com.smartcampus.backend.service.EmailService;
import com.smartcampus.backend.service.JwtService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UtilisateurRepository utilisateurRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final EmailService emailService;

    public AuthController(
            UtilisateurRepository utilisateurRepository,
            PasswordEncoder passwordEncoder,
            JwtService jwtService,
            EmailService emailService
    ) {
        this.utilisateurRepository = utilisateurRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
        this.emailService = emailService;
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

    /**
     * NOUVEAU — déclenche l'envoi d'un email avec un lien de
     * réinitialisation. Répond TOUJOURS pareil, que l'email existe ou
     * non dans la base — évite de révéler à un attaquant quels emails
     * correspondent à de vrais comptes (énumération de comptes).
     */
    @PostMapping("/mot-de-passe-oublie")
    public Map<String, String> motDePasseOublie(@Valid @RequestBody ForgotPasswordRequest request) {
        Optional<Utilisateur> utilisateurOpt = utilisateurRepository.findByEmail(request.getEmail());

        if (utilisateurOpt.isPresent()) {
            Utilisateur utilisateur = utilisateurOpt.get();
            String token = UUID.randomUUID().toString();

            utilisateur.setTokenReinitialisation(token);
            utilisateur.setTokenReinitialisationExpiration(Instant.now().plus(1, ChronoUnit.HOURS));
            utilisateurRepository.save(utilisateur);

            emailService.envoyerEmailReinitialisation(utilisateur.getEmail(), utilisateur.getPrenom(), token);
        }

        return Map.of("message", "Si un compte existe avec cet email, un lien de réinitialisation vient d'être envoyé.");
    }

    /**
     * NOUVEAU — vérifie le token (existence + expiration), puis met à
     * jour le mot de passe. Le token est invalidé après usage, qu'il
     * ait servi ou non — évite toute réutilisation.
     */
    @PostMapping("/reinitialiser-mot-de-passe")
    public Map<String, String> reinitialiserMotDePasse(@Valid @RequestBody ResetPasswordRequest request) {
        Utilisateur utilisateur = utilisateurRepository.findByTokenReinitialisation(request.getToken())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "Lien de réinitialisation invalide"));

        if (utilisateur.getTokenReinitialisationExpiration() == null
                || Instant.now().isAfter(utilisateur.getTokenReinitialisationExpiration())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Ce lien de réinitialisation a expiré, veuillez en redemander un nouveau");
        }

        utilisateur.setMotDePasseHache(passwordEncoder.encode(request.getNouveauMotDePasse()));
        utilisateur.setTokenReinitialisation(null);
        utilisateur.setTokenReinitialisationExpiration(null);
        utilisateurRepository.save(utilisateur);

        return Map.of("message", "Mot de passe mis à jour avec succès.");
    }
}