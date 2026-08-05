package com.smartcampus.backend.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

@Document(collection = "alertes")
public class Alerte {

    @Id
    private String id;

    /** SPOOFING / ACCES_NON_AUTORISE / ACCES_INTERDIT / HORAIRE_INTERDIT */
    private String type;

    private String evenementId;

    /** NON_TRAITEE / TRAITEE */
    private String statut = "NON_TRAITEE";

    private Instant horodatage = Instant.now();

    public Alerte() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getType() { return type; }
    public void setType(String type) { this.type = type; }

    public String getEvenementId() { return evenementId; }
    public void setEvenementId(String evenementId) { this.evenementId = evenementId; }

    public String getStatut() { return statut; }
    public void setStatut(String statut) { this.statut = statut; }

    public Instant getHorodatage() { return horodatage; }
    public void setHorodatage(Instant horodatage) { this.horodatage = horodatage; }
}
