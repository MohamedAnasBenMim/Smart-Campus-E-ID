package com.smartcampus.backend.service;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.util.Date;

/**
 * Génère et vérifie les tokens JWT utilisés pour l'authentification.
 *
 * NOTE IMPORTANTE : la clé secrète ci-dessous est codée en dur pour la durée
 * du stage — à déplacer vers une variable d'environnement avant tout
 * déploiement réel (ne jamais committer une vraie clé de production dans
 * le code source).
 */
@Service
public class JwtService {

    // Clé d'au moins 256 bits (32 caractères), requise pour HS256.
    private static final String SECRET = "smart-campus-eid-cle-secrete-a-changer-avant-prod-2026";
    private static final SecretKey KEY = Keys.hmacShaKeyFor(SECRET.getBytes());

    private static final long EXPIRATION_MS = 8 * 60 * 60 * 1000; // 8 heures

    public String generateToken(String email, String role) {
        Date now = new Date();
        Date expiration = new Date(now.getTime() + EXPIRATION_MS);

        return Jwts.builder()
                .subject(email)
                .claim("role", role)
                .issuedAt(now)
                .expiration(expiration)
                .signWith(KEY)
                .compact();
    }

    public String extractEmail(String token) {
        return parseClaims(token).getSubject();
    }

    public String extractRole(String token) {
        return parseClaims(token).get("role", String.class);
    }

    public boolean isTokenValid(String token) {
        try {
            Claims claims = parseClaims(token);
            return claims.getExpiration().after(new Date());
        } catch (Exception e) {
            return false;
        }
    }

    private Claims parseClaims(String token) {
        return Jwts.parser()
                .verifyWith(KEY)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}