package com.smartcampus.backend.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

/**
 * Compte utilisateur permettant de se connecter au dashboard — DIFFÉRENT
 * de Personne (voir son commentaire pour la distinction).
 *
 * Le mot de passe n'est JAMAIS stocké en clair — toujours haché (BCrypt,
 * via PasswordEncoder), y compris pour le tout premier compte créé au
 * démarrage (voir DataInitializer).
 */
@Document(collection = "utilisateurs")
public class Utilisateur {

    @Id
    private String id;

    private String nom;

    private String prenom;

    /** Sert d'identifiant de connexion (login) — doit être unique. */
    private String email;

    /** Toujours haché (BCrypt), jamais en clair. */
    private String motDePasseHache;

    /** ADMIN ou SURVEILLANT */
    private String role;

    /** ACTIF / INACTIF — permet de désactiver un compte sans le supprimer. */
    private String statut = "ACTIF";

    private Instant creeLe = Instant.now();

    public Utilisateur() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getNom() { return nom; }
    public void setNom(String nom) { this.nom = nom; }

    public String getPrenom() { return prenom; }
    public void setPrenom(String prenom) { this.prenom = prenom; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getMotDePasseHache() { return motDePasseHache; }
    public void setMotDePasseHache(String motDePasseHache) { this.motDePasseHache = motDePasseHache; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public String getStatut() { return statut; }
    public void setStatut(String statut) { this.statut = statut; }

    public Instant getCreeLe() { return creeLe; }
    public void setCreeLe(Instant creeLe) { this.creeLe = creeLe; }
}