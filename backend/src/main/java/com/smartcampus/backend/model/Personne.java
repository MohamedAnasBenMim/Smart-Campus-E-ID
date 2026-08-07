package com.smartcampus.backend.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;

/**
 * BF-01 / BF-03 — Profil d'une personne enrôlée (reconnue par caméra).
 * DIFFÉRENT de Utilisateur (comptes avec login/mot de passe pour le dashboard) —
 * une Personne peut ne jamais se connecter à la plateforme, elle est juste
 * "vue" par les caméras. Un même humain peut avoir les deux (ex. un surveillant
 * a un Utilisateur pour se connecter, ET une Personne s'il est aussi reconnu
 * par les caméras) — les deux entités restent volontairement indépendantes.
 */
@Document(collection = "personnes")
public class Personne {

    @Id
    private String id;

    private String nom;

    /** Optionnel */
    private String prenom;

    /** Optionnel */
    private String email;

    /** Optionnel */
    private String telephone;

    /** SURVEILLANT, DIRECTEUR, AGENT_DE_DIRECTION, PROF, ELEVE, PERSONNEL */
    private String role;

    /** Vecteur d'embedding — 128 valeurs (dlib) ou 512 (InsightFace) selon le service utilisé. */
    private List<Double> embedding;

    /** ACTIF / INACTIF — BF-04 */
    private String statut = "ACTIF";

    private Instant creeLe = Instant.now();

    public Personne() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getNom() { return nom; }
    public void setNom(String nom) { this.nom = nom; }

    public String getPrenom() { return prenom; }
    public void setPrenom(String prenom) { this.prenom = prenom; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getTelephone() { return telephone; }
    public void setTelephone(String telephone) { this.telephone = telephone; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public List<Double> getEmbedding() { return embedding; }
    public void setEmbedding(List<Double> embedding) { this.embedding = embedding; }

    public String getStatut() { return statut; }
    public void setStatut(String statut) { this.statut = statut; }

    public Instant getCreeLe() { return creeLe; }
    public void setCreeLe(Instant creeLe) { this.creeLe = creeLe; }
}