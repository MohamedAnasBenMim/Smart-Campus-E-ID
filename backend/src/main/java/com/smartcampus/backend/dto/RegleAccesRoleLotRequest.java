package com.smartcampus.backend.dto;

import java.time.LocalTime;
import java.util.List;

/**
 * Requête de création GROUPÉE — un rôle, PLUSIEURS zones sélectionnées
 * d'un coup, un seul horaire. Évite de répéter la même action pour
 * chaque salle une par une.
 */
public class RegleAccesRoleLotRequest {

    private String role;
    private List<String> zoneIds;
    private LocalTime horaireDebut;
    private LocalTime horaireFin;

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public List<String> getZoneIds() { return zoneIds; }
    public void setZoneIds(List<String> zoneIds) { this.zoneIds = zoneIds; }

    public LocalTime getHoraireDebut() { return horaireDebut; }
    public void setHoraireDebut(LocalTime horaireDebut) { this.horaireDebut = horaireDebut; }

    public LocalTime getHoraireFin() { return horaireFin; }
    public void setHoraireFin(LocalTime horaireFin) { this.horaireFin = horaireFin; }
}