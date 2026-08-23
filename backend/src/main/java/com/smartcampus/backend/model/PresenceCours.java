package com.smartcampus.backend.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

/**
 * L'appel RÉEL, pour UNE séance précise d'un Cours, à UNE date précise.
 *
 * Le Cours (autre modèle) définit le créneau RÉCURRENT (même horaire
 * chaque semaine) ; PresenceCours enregistre ce qui s'est VRAIMENT
 * passé ce jour-là précisément — présent, absent, en retard.
 */
@Document(collection = "presence_cours")
public class PresenceCours {

    @Id
    private String id;

    private String coursId;
    private LocalDate date;

    private List<PresenceIndividuelle> presencesEleves;
    private PresenceIndividuelle presenceProf;

    /**
     * "PREREMPLIE" : générée automatiquement à partir des événements
     * d'accès, PAS ENCORE validée par un humain — juste une proposition.
     * "VALIDEE" : confirmée (avec corrections éventuelles) par le prof
     * ou l'admin — c'est SEULEMENT à ce moment qu'elle est vraiment
     * enregistrée en base.
     */
    private String statutSeance = "PREREMPLIE";

    /** Email de la personne qui a validé l'appel */
    private String marqueePar;
    private Instant dateMarquage;

    public PresenceCours() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getCoursId() { return coursId; }
    public void setCoursId(String coursId) { this.coursId = coursId; }

    public LocalDate getDate() { return date; }
    public void setDate(LocalDate date) { this.date = date; }

    public List<PresenceIndividuelle> getPresencesEleves() { return presencesEleves; }
    public void setPresencesEleves(List<PresenceIndividuelle> presencesEleves) { this.presencesEleves = presencesEleves; }

    public PresenceIndividuelle getPresenceProf() { return presenceProf; }
    public void setPresenceProf(PresenceIndividuelle presenceProf) { this.presenceProf = presenceProf; }

    public String getStatutSeance() { return statutSeance; }
    public void setStatutSeance(String statutSeance) { this.statutSeance = statutSeance; }

    public String getMarqueePar() { return marqueePar; }
    public void setMarqueePar(String marqueePar) { this.marqueePar = marqueePar; }

    public Instant getDateMarquage() { return dateMarquage; }
    public void setDateMarquage(Instant dateMarquage) { this.dateMarquage = dateMarquage; }
}