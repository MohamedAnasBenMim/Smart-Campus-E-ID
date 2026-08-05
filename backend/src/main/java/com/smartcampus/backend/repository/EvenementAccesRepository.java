package com.smartcampus.backend.repository;

import com.smartcampus.backend.model.EvenementAcces;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface EvenementAccesRepository extends MongoRepository<EvenementAcces, String> {
}
