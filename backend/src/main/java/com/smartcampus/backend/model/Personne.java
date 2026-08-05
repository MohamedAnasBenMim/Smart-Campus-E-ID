package com.smartcampus.backend.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;

/**
 * BF-01 / BF-03 — Profil d'une personne enrôlée.
 * L'embedding est calculé par le service Python (FastAPI) à l'enrôlement,
 * puis stocké ICI, en base — Spring Boot est la seule source de vérité
 * pour la persistance, le service Python ne garde qu'une copie en mémoire.
 */
@Document(collection = "personnes")
public class Personne {

    @Id
    private String id;

    private String nom;

    /** ELEVE, PROFESSEUR, SURVEILLANT, ADMIN, VISITEUR */
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

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public List<Double> getEmbedding() { return embedding; }
    public void setEmbedding(List<Double> embedding) { this.embedding = embedding; }

    public String getStatut() { return statut; }
    public void setStatut(String statut) { this.statut = statut; }

    public Instant getCreeLe() { return creeLe; }
    public void setCreeLe(Instant creeLe) { this.creeLe = creeLe; }
}
