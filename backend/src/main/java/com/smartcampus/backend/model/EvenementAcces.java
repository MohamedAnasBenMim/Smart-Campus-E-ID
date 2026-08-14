package com.smartcampus.backend.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

/**
 * BF-09 — Trace de chaque tentative d'accès, quel que soit le résultat.
 * personneId est nullable : une personne non reconnue génère quand même
 * un événement (avec personneId = null), pour garder une trace complète.
 */
@Document(collection = "evenements_acces")
public class EvenementAcces {

    @Id
    private String id;

    private String personneId; 

    private String zoneId;

    private Instant horodatage = Instant.now();

    /** ACCORDE / REFUSE */
    private String resultat;

    /** ex: "hors horaire", "zone non autorisée", "spoofing détecté", "personne inconnue" */
    private String raison;

    /**
     * NOUVEAU : capture de l'image au moment exact de l'événement
     * (base64, préfixée "data:image/...;base64,") — pour l'historique
     * de présence dans le dashboard. Peut être null si la capture a
     * échoué (ne bloque jamais la journalisation elle-même).
     */
    private String capturePhoto;

    public EvenementAcces() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getPersonneId() { return personneId; }
    public void setPersonneId(String personneId) { this.personneId = personneId; }

    public String getZoneId() { return zoneId; }
    public void setZoneId(String zoneId) { this.zoneId = zoneId; }

    public Instant getHorodatage() { return horodatage; }
    public void setHorodatage(Instant horodatage) { this.horodatage = horodatage; }

    public String getResultat() { return resultat; }
    public void setResultat(String resultat) { this.resultat = resultat; }

    public String getRaison() { return raison; }
    public void setRaison(String raison) { this.raison = raison; }

    public String getCapturePhoto() { return capturePhoto; }
    public void setCapturePhoto(String capturePhoto) { this.capturePhoto = capturePhoto; }
}