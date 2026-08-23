package com.smartcampus.backend.model;

/**
 * Le statut de présence d'UNE personne (élève ou prof), pour UNE
 * séance précise d'un cours. Réutilisé à la fois pour les élèves et
 * pour le professeur — même logique pour les deux.
 */
public class PresenceIndividuelle {

    private String personneId;

    /** PRESENT, ABSENT, RETARD */
    private String statut;

    /** "HH:mm:ss", uniquement si PRESENT ou RETARD — null si ABSENT */
    private String heureArrivee;

    public PresenceIndividuelle() {}

    public PresenceIndividuelle(String personneId, String statut, String heureArrivee) {
        this.personneId = personneId;
        this.statut = statut;
        this.heureArrivee = heureArrivee;
    }

    public String getPersonneId() { return personneId; }
    public void setPersonneId(String personneId) { this.personneId = personneId; }

    public String getStatut() { return statut; }
    public void setStatut(String statut) { this.statut = statut; }

    public String getHeureArrivee() { return heureArrivee; }
    public void setHeureArrivee(String heureArrivee) { this.heureArrivee = heureArrivee; }
}