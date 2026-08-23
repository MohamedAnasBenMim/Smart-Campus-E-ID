package com.smartcampus.backend.repository;

import com.smartcampus.backend.model.PresenceCours;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface PresenceCoursRepository extends MongoRepository<PresenceCours, String> {
    List<PresenceCours> findByCoursId(String coursId);
    Optional<PresenceCours> findByCoursIdAndDate(String coursId, LocalDate date);
    List<PresenceCours> findByDate(LocalDate date);
}