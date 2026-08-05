package com.smartcampus.backend.service;

import com.smartcampus.backend.dto.FaceServiceResult;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;


@Service
public class FaceServiceClient {

    private final RestTemplate restTemplate;

    @Value("${face-service.base-url}")
    private String baseUrl;

    public FaceServiceClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    @SuppressWarnings("unchecked")
    public List<Double> enroll(String subjectId, List<MultipartFile> images) throws IOException {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("subject_id", subjectId);
        for (MultipartFile image : images) {
            body.add("images", toResource(image));
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);

        Map<String, Object> response = restTemplate.postForObject(baseUrl + "/enroll", request, Map.class);
        if (response == null || !response.containsKey("embedding")) {
            throw new IllegalStateException("Le service de reconnaissance n'a renvoyé aucun embedding.");
        }
        return (List<Double>) response.get("embedding");
    }

    public FaceServiceResult recognize(MultipartFile image) throws IOException {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("image", toResource(image));

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);

        FaceServiceResult result = restTemplate.postForObject(baseUrl + "/recognize", request, FaceServiceResult.class);
        if (result == null) {
            throw new IllegalStateException("Le service de reconnaissance n'a renvoyé aucune réponse.");
        }
        return result;
    }

    private ByteArrayResource toResource(MultipartFile file) throws IOException {
        return new ByteArrayResource(file.getBytes()) {
            @Override
            public String getFilename() {
                return file.getOriginalFilename();
            }
        };
    }
}
