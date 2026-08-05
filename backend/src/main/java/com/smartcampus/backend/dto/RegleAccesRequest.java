package com.smartcampus.backend.dto;

import jakarta.validation.constraints.NotBlank;

public class RegleAccesRequest {

    @NotBlank
    private String personneId;

    @NotBlank
    private String zoneId;

    @NotBlank
    private String horaireDebut;

    @NotBlank
    private String horaireFin;

    public String getPersonneId() { return personneId; }
    public void setPersonneId(String personneId) { this.personneId = personneId; }

    public String getZoneId() { return zoneId; }
    public void setZoneId(String zoneId) { this.zoneId = zoneId; }

    public String getHoraireDebut() { return horaireDebut; }
    public void setHoraireDebut(String horaireDebut) { this.horaireDebut = horaireDebut; }

    public String getHoraireFin() { return horaireFin; }
    public void setHoraireFin(String horaireFin) { this.horaireFin = horaireFin; }
}
