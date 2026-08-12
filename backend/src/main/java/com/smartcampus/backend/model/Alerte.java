package com.smartcampus.backend.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

@Document(collection = "alertes")
public class Alerte {

    @Id
    private String id;

    /** SPOOFING / ACCES_NON_AUTORISE / ACCES_INTERDIT / HORAIRE_INTERDIT / PRESENCE_NON_IDENTIFIEE / IDENTITE_A_CONFIRMER */
    private String type;

    private String evenementId;

    /** NON_TRAITEE / TRAITEE */
    private String statut = "NON_TRAITEE";

    private Instant horodatage = Instant.now();

    // ---- NOUVEAU : suivi du traitement (demandé par l'encadrant) ----

    /** Explication de l'admin/surveillant : comment l'alerte a été gérée concrètement. */
    private String commentaireTraitement;

    /** Email de l'utilisateur (Admin/Surveillant) qui a traité l'alerte. */
    private String traitePar;

    /** Renseigné automatiquement au moment où le statut passe à TRAITEE. */
    private Instant dateTraitement;

    /**
     * NOUVEAU : capture de l'image au moment exact de l'alerte (encodée en
     * base64, préfixée "data:image/...;base64,") — pour que le surveillant
     * voie immédiatement de quoi/qui il s'agit, sans avoir à chercher dans
     * un flux vidéo. Peut être null si la capture a échoué (ne bloque jamais
     * la création de l'alerte elle-même).
     */
    private String capturePhoto;

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

    public String getCommentaireTraitement() { return commentaireTraitement; }
    public void setCommentaireTraitement(String commentaireTraitement) { this.commentaireTraitement = commentaireTraitement; }

    public String getTraitePar() { return traitePar; }
    public void setTraitePar(String traitePar) { this.traitePar = traitePar; }

    public Instant getDateTraitement() { return dateTraitement; }
    public void setDateTraitement(Instant dateTraitement) { this.dateTraitement = dateTraitement; }

    public String getCapturePhoto() { return capturePhoto; }
    public void setCapturePhoto(String capturePhoto) { this.capturePhoto = capturePhoto; }
}