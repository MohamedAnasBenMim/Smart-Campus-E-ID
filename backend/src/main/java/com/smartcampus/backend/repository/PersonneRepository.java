package com.smartcampus.backend.repository;

import com.smartcampus.backend.model.Personne;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface PersonneRepository extends MongoRepository<Personne, String> {
}
