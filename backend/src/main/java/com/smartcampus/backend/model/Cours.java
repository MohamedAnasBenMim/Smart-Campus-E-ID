package com.smartcampus.backend.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalTime;

/**
 * Un cours = un créneau RÉCURRENT, pour UNE classe entière.
 *
 * La liste des élèves concernés vient de la Classe (classeId), PAS
 * d'ici — évite de la ressaisir à chaque cours et garantit qu'elle
 * reste cohérente entre tous les cours d'une même classe.
 *
 * Sert aussi pour la présence du PROF (profId) — même logique que
 * pour les élèves : "était-il dans sa salle, à son horaire prévu ?".
 */
@Document(collection = "cours")
public class Cours {

    @Id
    private String id;

    /** ex. "Mathématiques" */
    private String nom;

    private String classeId;

    /** Personne avec role=PROF */
    private String profId;

    /** La salle où se déroule le cours */
    private String zoneId;

    /** LUNDI, MARDI, MERCREDI, JEUDI, VENDREDI, SAMEDI */
    private String jourSemaine;

    private LocalTime heureDebut;
    private LocalTime heureFin;

    public Cours() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getNom() { return nom; }
    public void setNom(String nom) { this.nom = nom; }

    public String getClasseId() { return classeId; }
    public void setClasseId(String classeId) { this.classeId = classeId; }

    public String getProfId() { return profId; }
    public void setProfId(String profId) { this.profId = profId; }

    public String getZoneId() { return zoneId; }
    public void setZoneId(String zoneId) { this.zoneId = zoneId; }

    public String getJourSemaine() { return jourSemaine; }
    public void setJourSemaine(String jourSemaine) { this.jourSemaine = jourSemaine; }

    public LocalTime getHeureDebut() { return heureDebut; }
    public void setHeureDebut(LocalTime heureDebut) { this.heureDebut = heureDebut; }

    public LocalTime getHeureFin() { return heureFin; }
    public void setHeureFin(LocalTime heureFin) { this.heureFin = heureFin; }
}