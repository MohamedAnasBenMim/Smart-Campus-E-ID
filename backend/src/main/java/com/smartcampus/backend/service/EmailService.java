package com.smartcampus.backend.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;

/**
 * Envoi d'emails — pour l'instant, uniquement la réinitialisation de
 * mot de passe. Utilise la configuration SMTP définie dans
 * application.properties (spring.mail.*).
 */
@Service
public class EmailService {

    private static final Logger log = LoggerFactory.getLogger(EmailService.class);

    private final JavaMailSender mailSender;

    @Value("${app.frontend-url}")
    private String frontendUrl;

    public EmailService(JavaMailSender mailSender) {
        this.mailSender = mailSender;
    }

    public void envoyerEmailReinitialisation(String destinataire, String prenom, String token) {
        String lien = frontendUrl + "/reinitialiser-mot-de-passe?token=" + token;

        SimpleMailMessage message = new SimpleMailMessage();
        message.setTo(destinataire);
        message.setSubject("Smart Campus E-ID — Réinitialisation de votre mot de passe");
        message.setText(
                "Bonjour " + (prenom != null ? prenom : "") + ",\n\n"
                        + "Une demande de réinitialisation de mot de passe a été effectuée pour votre compte.\n\n"
                        + "Cliquez sur ce lien pour choisir un nouveau mot de passe (valable 1 heure) :\n"
                        + lien + "\n\n"
                        + "Si vous n'êtes pas à l'origine de cette demande, ignorez simplement cet email — "
                        + "votre mot de passe actuel reste inchangé.\n\n"
                        + "— Smart Campus E-ID"
        );

        try {
            mailSender.send(message);
            log.info("Email de réinitialisation envoyé à {}", destinataire);
        } catch (Exception e) {
            // Ne fait JAMAIS échouer la requête HTTP pour l'utilisateur —
            // évite de révéler des détails techniques internes, et le
            // comportement "toujours répondre pareil" reste cohérent
            // que l'envoi réussisse ou non côté serveur SMTP.
            log.error("Échec de l'envoi de l'email de réinitialisation à {} : {}", destinataire, e.getMessage());
        }
    }
}