package kr.co.mdesk;

import kr.co.mdesk.config.JwtProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(JwtProperties.class)
public class MdeskApiApplication {

    public static void main(String[] args) {
        SpringApplication.run(MdeskApiApplication.class, args);
    }
}
