package com.smartcampus.backend.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalTime;

/**
 * BF-08 — Associe une personne à une zone, avec une plage horaire autorisée.
 * La vérification "cette personne a-t-elle le droit d'être ici, maintenant ?"
 * consiste à chercher une RegleAcces correspondante et vérifier l'horaire.
 */
@Document(collection = "regles_acces")
public class RegleAcces {

    @Id
    private String id;

    private String personneId;

    private String zoneId;

    private LocalTime horaireDebut;

    private LocalTime horaireFin;

    public RegleAcces() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getPersonneId() { return personneId; }
    public void setPersonneId(String personneId) { this.personneId = personneId; }

    public String getZoneId() { return zoneId; }
    public void setZoneId(String zoneId) { this.zoneId = zoneId; }

    public LocalTime getHoraireDebut() { return horaireDebut; }
    public void setHoraireDebut(LocalTime horaireDebut) { this.horaireDebut = horaireDebut; }

    public LocalTime getHoraireFin() { return horaireFin; }
    public void setHoraireFin(LocalTime horaireFin) { this.horaireFin = horaireFin; }
}
