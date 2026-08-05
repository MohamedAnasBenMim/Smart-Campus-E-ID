package com.smartcampus.backend.config;

import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.mongodb.MongoDatabaseFactory;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.SimpleMongoClientDatabaseFactory;

/**
 * Configuration MongoDB explicite, écrite directement en code plutôt que
 * via application.properties/yaml/variables d'environnement.
 *
 * Pourquoi : après plusieurs tentatives (fichier YAML, .properties, variable
 * d'environnement pour l'URI, puis pour host/port/database séparément), la
 * configuration automatique de Spring Boot 4 continue à se connecter à
 * localhost au lieu de "mongo", quelle que soit la méthode utilisée — un
 * comportement qui correspond à un bug documenté sur le repo GitHub officiel
 * de Spring Boot concernant la liaison de MongoProperties dans cette version.
 *
 * Cette classe définit les beans nécessaires "à la main", ce qui prend le
 * pas sur l'auto-configuration de Spring Boot (qui ne s'active que si CES
 * beans n'existent pas déjà) — plus aucune propriété à faire deviner à Spring.
 */
@Configuration
public class MongoConfig {

    private static final String MONGO_URI = "mongodb://mongo:27017/smartcampus";
    private static final String DATABASE_NAME = "smartcampus";

    @Bean
    public MongoClient mongoClient() {
        return MongoClients.create(MONGO_URI);
    }

    @Bean
    public MongoDatabaseFactory mongoDatabaseFactory(MongoClient mongoClient) {
        return new SimpleMongoClientDatabaseFactory(mongoClient, DATABASE_NAME);
    }

    @Bean
    public MongoTemplate mongoTemplate(MongoDatabaseFactory mongoDatabaseFactory) {
        return new MongoTemplate(mongoDatabaseFactory);
    }
}