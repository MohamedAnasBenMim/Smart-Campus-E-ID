package com.smartcampus.backend.controller;

import com.smartcampus.backend.model.PresenceCours;
import com.smartcampus.backend.service.PresenceCoursService;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/presence-cours")
public class PresenceCoursController {

    private final PresenceCoursService service;

    public PresenceCoursController(PresenceCoursService service) {
        this.service = service;
    }

    /**
     * Calcule une PROPOSITION d'appel à partir des événements d'accès
     * déjà enregistrés — NE SAUVEGARDE RIEN.
     */
    @GetMapping("/preremplir")
    public PresenceCours preremplir(
            @RequestParam String coursId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date
    ) {
        return service.preremplir(coursId, date);
    }

    /** Enregistre l'appel définitif, après relecture/correction humaine. */
    @PostMapping
    public PresenceCours valider(@RequestBody PresenceCours saisie, Authentication authentication) {
        return service.valider(saisie, authentication.getName());
    }

    /**
     * NOUVEAU : sans aucun paramètre, renvoie TOUS les appels déjà
     * validés — utilisé par la page "Historique des appels", qui
     * filtre ensuite par classe/date côté dashboard.
     */
    @GetMapping
    public List<PresenceCours> lister(
            @RequestParam(required = false) String coursId,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date
    ) {
        if (coursId != null && date != null) {
            return service.trouver(coursId, date).map(List::of).orElse(List.of());
        }
        if (coursId != null) return service.listerParCours(coursId);
        if (date != null) return service.listerParDate(date);
        return service.listerTous();
    }
}