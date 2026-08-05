package com.smartcampus.backend.repository;

import com.smartcampus.backend.model.Zone;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface ZoneRepository extends MongoRepository<Zone, String> {
}
