package com.smartcampus.backend.service;

import com.smartcampus.backend.model.Classe;
import com.smartcampus.backend.model.Cours;
import com.smartcampus.backend.model.EvenementAcces;
import com.smartcampus.backend.model.PresenceCours;
import com.smartcampus.backend.model.PresenceIndividuelle;
import com.smartcampus.backend.repository.ClasseRepository;
import com.smartcampus.backend.repository.CoursRepository;
import com.smartcampus.backend.repository.EvenementAccesRepository;
import com.smartcampus.backend.repository.PresenceCoursRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * Cœur du système de présence : ne demande JAMAIS à un prof de saisir
 * manuellement qui est présent depuis zéro — croise systématiquement
 * avec les EvenementAcces déjà enregistrés (la personne est-elle
 * passée dans LA salle du cours, PENDANT le créneau ?), et propose un
 * appel PRÉ-REMPLI que l'humain n'a plus qu'à valider ou corriger.
 *
 * IMPORTANT : preremplir() ne sauvegarde RIEN — c'est un calcul à la
 * volée, une simple proposition. Seul valider() persiste réellement,
 * après passage humain.
 *
 * NOUVEAU : trouver() permet de retrouver un appel DÉJÀ VALIDÉ pour
 * une date passée — sans ça, rouvrir l'appel d'un jour précédent
 * recalculait toujours une nouvelle proposition, en ignorant ce qui
 * avait déjà été validé et éventuellement corrigé par un humain.
 */
@Service
public class PresenceCoursService {

    // Un passage plus de X minutes après le début du créneau compte
    // comme un retard, pas une présence normale.
    private static final long SEUIL_RETARD_MINUTES = 10;

    private final CoursRepository coursRepository;
    private final ClasseRepository classeRepository;
    private final EvenementAccesRepository evenementAccesRepository;
    private final PresenceCoursRepository presenceCoursRepository;

    public PresenceCoursService(
            CoursRepository coursRepository,
            ClasseRepository classeRepository,
            EvenementAccesRepository evenementAccesRepository,
            PresenceCoursRepository presenceCoursRepository
    ) {
        this.coursRepository = coursRepository;
        this.classeRepository = classeRepository;
        this.evenementAccesRepository = evenementAccesRepository;
        this.presenceCoursRepository = presenceCoursRepository;
    }

    /**
     * NOUVEAU — retrouve l'appel déjà VALIDÉ pour ce cours, à cette
     * date précise, s'il existe. Ne calcule rien, lit juste la base.
     */
    public Optional<PresenceCours> trouver(String coursId, LocalDate date) {
        return presenceCoursRepository.findByCoursIdAndDate(coursId, date);
    }

    public PresenceCours preremplir(String coursId, LocalDate date) {
        Cours cours = coursRepository.findById(coursId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Cours introuvable"));

        Classe classe = classeRepository.findById(cours.getClasseId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Classe introuvable pour ce cours"));

        Instant debutCreneau = date.atTime(cours.getHeureDebut()).atZone(ZoneId.systemDefault()).toInstant();
        Instant finCreneau = date.atTime(cours.getHeureFin()).atZone(ZoneId.systemDefault()).toInstant();

        // Tous les accès ACCORDÉS dans LA salle de ce cours, PENDANT ce créneau précis.
        List<EvenementAcces> evenementsPertinents = evenementAccesRepository.findAll().stream()
                .filter(e -> cours.getZoneId().equals(e.getZoneId()))
                .filter(e -> "ACCORDE".equals(e.getResultat()))
                .filter(e -> e.getHorodatage() != null
                        && !e.getHorodatage().isBefore(debutCreneau)
                        && !e.getHorodatage().isAfter(finCreneau))
                .collect(Collectors.toList());

        // Pour chaque personne, on ne garde que son PREMIER passage dans
        // le créneau — inutile de garder les suivants pour un appel.
        Map<String, Instant> premierPassageParPersonne = new HashMap<>();
        for (EvenementAcces e : evenementsPertinents) {
            premierPassageParPersonne.merge(
                    e.getPersonneId(), e.getHorodatage(),
                    (existant, nouveau) -> existant.isBefore(nouveau) ? existant : nouveau
            );
        }

        List<PresenceIndividuelle> presencesEleves = new ArrayList<>();
        if (classe.getEleveIds() != null) {
            for (String eleveId : classe.getEleveIds()) {
                presencesEleves.add(construirePresence(eleveId, premierPassageParPersonne.get(eleveId), debutCreneau));
            }
        }

        PresenceIndividuelle presenceProf = construirePresence(
                cours.getProfId(), premierPassageParPersonne.get(cours.getProfId()), debutCreneau
        );

        PresenceCours resultat = new PresenceCours();
        resultat.setCoursId(coursId);
        resultat.setDate(date);
        resultat.setPresencesEleves(presencesEleves);
        resultat.setPresenceProf(presenceProf);
        resultat.setStatutSeance("PREREMPLIE");

        return resultat;
    }

    private PresenceIndividuelle construirePresence(String personneId, Instant passage, Instant debutCreneau) {
        if (passage == null) {
            return new PresenceIndividuelle(personneId, "ABSENT", null);
        }

        String heureArrivee = passage.atZone(ZoneId.systemDefault()).toLocalTime().toString();
        boolean enRetard = Duration.between(debutCreneau, passage).toMinutes() > SEUIL_RETARD_MINUTES;

        return new PresenceIndividuelle(personneId, enRetard ? "RETARD" : "PRESENT", heureArrivee);
    }

    /**
     * Enregistre l'appel définitif — après relecture et corrections
     * éventuelles par un humain. Si un appel existe déjà pour ce
     * cours/cette date, il est REMPLACÉ (pas dupliqué).
     */
    public PresenceCours valider(PresenceCours saisie, String marqueePar) {
        if (saisie.getCoursId() == null || saisie.getDate() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "coursId et date requis");
        }

        Optional<PresenceCours> existant = presenceCoursRepository.findByCoursIdAndDate(saisie.getCoursId(), saisie.getDate());
        existant.ifPresent(p -> saisie.setId(p.getId()));

        saisie.setStatutSeance("VALIDEE");
        saisie.setMarqueePar(marqueePar);
        saisie.setDateMarquage(Instant.now());

        return presenceCoursRepository.save(saisie);
    }

    public List<PresenceCours> listerParCours(String coursId) {
        return presenceCoursRepository.findByCoursId(coursId);
    }

    public List<PresenceCours> listerParDate(LocalDate date) {
        return presenceCoursRepository.findByDate(date);
    }

    /** NOUVEAU — tous les appels déjà validés, sans filtre. */
    public List<PresenceCours> listerTous() {
        return presenceCoursRepository.findAll();
    }
}