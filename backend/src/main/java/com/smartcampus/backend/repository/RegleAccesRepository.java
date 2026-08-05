package com.smartcampus.backend.repository;

import com.smartcampus.backend.model.RegleAcces;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface RegleAccesRepository extends MongoRepository<RegleAcces, String> {

    Optional<RegleAcces> findByPersonneIdAndZoneId(String personneId, String zoneId);

    List<RegleAcces> findByPersonneId(String personneId);
}
