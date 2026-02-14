package kr.co.mdesk.repository.work;

import java.util.Optional;
import kr.co.mdesk.domain.work.RustDeskToken;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RustDeskTokenRepository extends JpaRepository<RustDeskToken, Long> {

    Optional<RustDeskToken> findByAccessToken(String accessToken);

    Optional<RustDeskToken> findFirstByUidAndUsernameAndRid(String uid, String username, String rid);

    Optional<RustDeskToken> findFirstByUidAndRid(String uid, String rid);
}
