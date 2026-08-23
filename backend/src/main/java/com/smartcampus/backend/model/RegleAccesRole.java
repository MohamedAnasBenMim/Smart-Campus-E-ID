package com.smartcampus.backend.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalTime;

/**
 * Règle d'accès GÉNÉRALE, par rôle plutôt que par personne — évite de
 * créer une règle individuelle pour chacune des centaines de
 * personnes d'un établissement.
 *
 * Typiquement utilisée pour le personnel qui n'a pas d'emploi du
 * temps de cours (surveillants, direction, agents...) — élèves et
 * profs sont, eux, couverts automatiquement par leurs Cours (voir
 * AccessDecisionService), sans avoir besoin de règle du tout dans le
 * cas général.
 */
@Document(collection = "regles_acces_role")
public class RegleAccesRole {

    @Id
    private String id;

    /** SURVEILLANT, DIRECTEUR, AGENT_DE_DIRECTION, PROF, ELEVE, PERSONNEL */
    private String role;

    private String zoneId;

    private LocalTime horaireDebut;
    private LocalTime horaireFin;

    public RegleAccesRole() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public String getZoneId() { return zoneId; }
    public void setZoneId(String zoneId) { this.zoneId = zoneId; }

    public LocalTime getHoraireDebut() { return horaireDebut; }
    public void setHoraireDebut(LocalTime horaireDebut) { this.horaireDebut = horaireDebut; }

    public LocalTime getHoraireFin() { return horaireFin; }
    public void setHoraireFin(LocalTime horaireFin) { this.horaireFin = horaireFin; }
}