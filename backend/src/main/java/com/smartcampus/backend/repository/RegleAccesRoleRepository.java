package com.smartcampus.backend.repository;

import com.smartcampus.backend.model.RegleAccesRole;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface RegleAccesRoleRepository extends MongoRepository<RegleAccesRole, String> {
    List<RegleAccesRole> findByRoleAndZoneId(String role, String zoneId);
}