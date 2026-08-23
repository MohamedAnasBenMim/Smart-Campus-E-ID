package com.smartcampus.backend.repository;

import com.smartcampus.backend.model.Classe;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface ClasseRepository extends MongoRepository<Classe, String> {
}