package com.smartcampus.backend.controller;

import com.smartcampus.backend.model.Classe;
import com.smartcampus.backend.repository.ClasseRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

/**
 * NOUVEAU : vérifie qu'un élève n'appartient jamais à deux classes en
 * même temps — un élève n'a qu'une seule classe, par définition.
 */
@RestController
@RequestMapping("/api/classes")
public class ClasseController {

    private final ClasseRepository classeRepository;

    public ClasseController(ClasseRepository classeRepository) {
        this.classeRepository = classeRepository;
    }

    @GetMapping
    public List<Classe> lister() {
        return classeRepository.findAll();
    }

    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Classe creer(@RequestBody Classe classe) {
        verifierElevesDisponibles(classe, null);
        return classeRepository.save(classe);
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Classe modifier(@PathVariable String id, @RequestBody Classe modifications) {
        Classe classe = classeRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Classe introuvable"));

        classe.setNom(modifications.getNom());
        classe.setEleveIds(modifications.getEleveIds());

        verifierElevesDisponibles(classe, id);

        return classeRepository.save(classe);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public void supprimer(@PathVariable String id) {
        classeRepository.deleteById(id);
    }

    /**
     * Rejette si un des élèves proposés appartient déjà à une AUTRE
     * classe (on s'ignore soi-même lors d'une modification).
     */
    private void verifierElevesDisponibles(Classe nouvelleClasse, String idAIgnorer) {
        if (nouvelleClasse.getEleveIds() == null || nouvelleClasse.getEleveIds().isEmpty()) {
            return;
        }

        List<Classe> toutesLesClasses = classeRepository.findAll();

        for (Classe existante : toutesLesClasses) {
            if (idAIgnorer != null && idAIgnorer.equals(existante.getId())) {
                continue;
            }
            if (existante.getEleveIds() == null) {
                continue;
            }

            for (String eleveId : nouvelleClasse.getEleveIds()) {
                if (existante.getEleveIds().contains(eleveId)) {
                    throw new ResponseStatusException(
                            HttpStatus.CONFLICT,
                            "Un ou plusieurs élèves sélectionnés sont déjà inscrits dans la classe \"" + existante.getNom() + "\""
                    );
                }
            }
        }
    }
}