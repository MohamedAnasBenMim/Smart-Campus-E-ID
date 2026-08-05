package com.smartcampus.backend.controller;

import com.smartcampus.backend.dto.AccessDecision;
import com.smartcampus.backend.service.AccessDecisionService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;

/**
 * Le point d'entrée qu'une caméra de zone (ou votre webcam_client.py adapté)
 * appellerait à chaque frame — c'est ici que se croisent identité et règles.
 */
@RestController
@RequestMapping("/api/access-events")
public class AccessController {

    private final AccessDecisionService accessDecisionService;

    public AccessController(AccessDecisionService accessDecisionService) {
        this.accessDecisionService = accessDecisionService;
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public List<AccessDecision> traiterFrame(
            @RequestParam("image") MultipartFile image,
            @RequestParam("zoneId") String zoneId
    ) throws IOException {
        return accessDecisionService.processFrame(image, zoneId);
    }
}
