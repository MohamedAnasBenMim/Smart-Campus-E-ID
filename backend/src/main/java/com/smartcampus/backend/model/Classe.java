package com.smartcampus.backend.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.util.List;

/**
 * Une classe (ex. "3ème B") — porte la liste des élèves UNE SEULE
 * FOIS, contrairement à l'ancien modèle où chaque Cours listait ses
 * propres élèves (répétitif, et risquait l'incohérence entre les
 * cours d'une même classe).
 *
 * "L'emploi du temps d'une classe" n'est PAS stocké ici — c'est
 * simplement l'ensemble des Cours dont classeId pointe vers cette
 * classe, calculé à la volée, pas une donnée dupliquée.
 */
@Document(collection = "classes")
public class Classe {

    @Id
    private String id;

    private String nom;

    /** Personnes avec role=ELEVE — un élève n'appartient qu'à une seule classe. */
    private List<String> eleveIds;

    public Classe() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getNom() { return nom; }
    public void setNom(String nom) { this.nom = nom; }

    public List<String> getEleveIds() { return eleveIds; }
    public void setEleveIds(List<String> eleveIds) { this.eleveIds = eleveIds; }
}