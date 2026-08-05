package com.smartcampus.backend.dto;

public class AccessDecision {

    private String personneId;
    private String nom;
    private String zoneId;
    private String resultat; // ACCORDE / REFUSE
    private String raison;

    public AccessDecision() {}

    public AccessDecision(String personneId, String nom, String zoneId, String resultat, String raison) {
        this.personneId = personneId;
        this.nom = nom;
        this.zoneId = zoneId;
        this.resultat = resultat;
        this.raison = raison;
    }

    public String getPersonneId() { return personneId; }
    public void setPersonneId(String personneId) { this.personneId = personneId; }

    public String getNom() { return nom; }
    public void setNom(String nom) { this.nom = nom; }

    public String getZoneId() { return zoneId; }
    public void setZoneId(String zoneId) { this.zoneId = zoneId; }

    public String getResultat() { return resultat; }
    public void setResultat(String resultat) { this.resultat = resultat; }

    public String getRaison() { return raison; }
    public void setRaison(String raison) { this.raison = raison; }
}
