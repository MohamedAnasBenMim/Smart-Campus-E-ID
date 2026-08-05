package com.smartcampus.backend.repository;

import com.smartcampus.backend.model.Alerte;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface AlerteRepository extends MongoRepository<Alerte, String> {
}
