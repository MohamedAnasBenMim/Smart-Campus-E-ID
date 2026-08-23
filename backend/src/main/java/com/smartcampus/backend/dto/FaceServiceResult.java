package com.smartcampus.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Reflète exactement le contrat JSON renvoyé par POST /recognize du service
 * Python (voir schemas.py côté FastAPI) : {"visages_detectes": N, "resultats": [...]}.
 */
public class FaceServiceResult {

    @JsonProperty("visages_detectes")
    private int visagesDetectes;

    @JsonProperty("personnes_detectees")
    private int personnesDetectees;

    @JsonProperty("presence_non_identifiee")
    private boolean presenceNonIdentifiee;

    private List<FaceResultItem> resultats;

    public int getVisagesDetectes() { return visagesDetectes; }
    public void setVisagesDetectes(int visagesDetectes) { this.visagesDetectes = visagesDetectes; }

    public int getPersonnesDetectees() { return personnesDetectees; }
    public void setPersonnesDetectees(int personnesDetectees) { this.personnesDetectees = personnesDetectees; }

    public boolean isPresenceNonIdentifiee() { return presenceNonIdentifiee; }
    public void setPresenceNonIdentifiee(boolean presenceNonIdentifiee) { this.presenceNonIdentifiee = presenceNonIdentifiee; }

    public List<FaceResultItem> getResultats() { return resultats; }
    public void setResultats(List<FaceResultItem> resultats) { this.resultats = resultats; }

    public static class FaceResultItem {
        private Boolean vivant;
        private String resultat;

        @JsonProperty("subject_id")
        private String subjectId;

        private Double confiance;
        private String raison;

        /**
         * NOUVEAU : présent uniquement quand le visage était trop petit
         * (sous MIN_FACE_WIDTH_PX) mais qu'une reconnaissance a quand même
         * été tentée — signale que ce résultat est moins fiable, à ne pas
         * traiter avec la même confiance qu'un résultat normal.
         */
        private String avertissement;

        /**
         * NOUVEAU : position du visage dans l'image [left, top, width, height],
         * en pixels — jusqu'ici reçue du service Python mais jamais déclarée
         * ici, donc silencieusement ignorée par Jackson. Nécessaire pour
         * dessiner un cadre sur la bonne personne dans les captures.
         */
        private List<Integer> bbox;

        /**
         * NOUVEAU : embedding du visage (512 valeurs), renvoyé par
         * face-service pour "reconnu" et "inconnu" — nécessaire pour le
         * traitement spécialisé des alertes.
         */
        private List<Double> embedding;

        public List<Double> getEmbedding() { return embedding; }
        public void setEmbedding(List<Double> embedding) { this.embedding = embedding; }

        public Boolean getVivant() { return vivant; }
        public void setVivant(Boolean vivant) { this.vivant = vivant; }

        public String getResultat() { return resultat; }
        public void setResultat(String resultat) { this.resultat = resultat; }

        public String getSubjectId() { return subjectId; }
        public void setSubjectId(String subjectId) { this.subjectId = subjectId; }

        public Double getConfiance() { return confiance; }
        public void setConfiance(Double confiance) { this.confiance = confiance; }

        public String getRaison() { return raison; }
        public void setRaison(String raison) { this.raison = raison; }

        public String getAvertissement() { return avertissement; }
        public void setAvertissement(String avertissement) { this.avertissement = avertissement; }

        public List<Integer> getBbox() { return bbox; }
        public void setBbox(List<Integer> bbox) { this.bbox = bbox; }
    }
}