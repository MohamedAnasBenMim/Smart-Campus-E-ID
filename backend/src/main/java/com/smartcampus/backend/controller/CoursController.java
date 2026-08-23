package com.smartcampus.backend.controller;

import com.smartcampus.backend.model.Cours;
import com.smartcampus.backend.repository.CoursRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalTime;
import java.util.List;

/**
 * NOUVEAU : vérifie systématiquement la disponibilité de la SALLE et
 * du PROF avant d'accepter un cours — sans ça, rien n'empêchait deux
 * cours différents de revendiquer la même salle, ou le même prof,
 * sur un créneau qui se chevauche.
 */
@RestController
@RequestMapping("/api/cours")
public class CoursController {

    private final CoursRepository coursRepository;

    public CoursController(CoursRepository coursRepository) {
        this.coursRepository = coursRepository;
    }

    @GetMapping
    public List<Cours> lister() {
        return coursRepository.findAll();
    }

    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Cours creer(@RequestBody Cours cours) {
        verifierDisponibilite(cours, null);
        return coursRepository.save(cours);
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Cours modifier(@PathVariable String id, @RequestBody Cours modifications) {
        Cours cours = coursRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Cours introuvable"));

        cours.setNom(modifications.getNom());
        cours.setClasseId(modifications.getClasseId());
        cours.setProfId(modifications.getProfId());
        cours.setZoneId(modifications.getZoneId());
        cours.setJourSemaine(modifications.getJourSemaine());
        cours.setHeureDebut(modifications.getHeureDebut());
        cours.setHeureFin(modifications.getHeureFin());

        // On s'ignore soi-même lors de la vérification — sinon un cours
        // entrerait toujours "en conflit" avec sa propre version actuelle.
        verifierDisponibilite(cours, id);

        return coursRepository.save(cours);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public void supprimer(@PathVariable String id) {
        coursRepository.deleteById(id);
    }

    /**
     * Rejette la création/modification si la salle OU le prof est déjà
     * engagé sur un créneau qui se chevauche, le même jour.
     */
    private void verifierDisponibilite(Cours nouveauCours, String idAIgnorer) {
        List<Cours> tousLesCours = coursRepository.findAll();

        for (Cours existant : tousLesCours) {
            if (idAIgnorer != null && idAIgnorer.equals(existant.getId())) {
                continue;
            }
            if (!existant.getJourSemaine().equals(nouveauCours.getJourSemaine())) {
                continue;
            }
            if (!creneauxSeChevauchent(
                    nouveauCours.getHeureDebut(), nouveauCours.getHeureFin(),
                    existant.getHeureDebut(), existant.getHeureFin()
            )) {
                continue;
            }

            if (existant.getZoneId().equals(nouveauCours.getZoneId())) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "Cette salle est déjà occupée sur ce créneau par le cours \"" + existant.getNom() + "\""
                );
            }

            if (existant.getProfId().equals(nouveauCours.getProfId())) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "Ce professeur assure déjà le cours \"" + existant.getNom() + "\" sur ce créneau"
                );
            }

            // NOUVEAU : la classe elle-même ne peut pas suivre deux cours
            // en même temps, même dans des salles différentes avec des
            // profs différents — elle est physiquement à un seul endroit.
            if (existant.getClasseId().equals(nouveauCours.getClasseId())) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "Cette classe a déjà le cours \"" + existant.getNom() + "\" sur ce créneau"
                );
            }
        }
    }

    private boolean creneauxSeChevauchent(LocalTime debut1, LocalTime fin1, LocalTime debut2, LocalTime fin2) {
        return debut1.isBefore(fin2) && debut2.isBefore(fin1);
    }
}