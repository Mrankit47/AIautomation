import pytest
import uuid
from sqlalchemy import select
from backend.database.session import get_sync_session
from backend.models.artwork import Artwork, ArtworkStatus

def database_available() -> bool:
    try:
        session = get_sync_session()
        # Execute a simple query to verify connection
        session.execute(select(1))
        session.close()
        return True
    except Exception:
        return False

@pytest.mark.skipif(not database_available(), reason="PostgreSQL database not available or credentials mismatch")
def test_postgres_enum_insertion() -> None:
    """Regression test ensuring ArtworkStatus.UPLOADED inserts successfully into PostgreSQL."""
    session = get_sync_session()
    artwork_id = uuid.uuid4()
    
    art = Artwork(
        id=artwork_id,
        title="PostgreSQL Regression Test",
        original_filename="test_pg_reg.png",
        file_path="artworks/test_pg_reg.png",
        file_size=1024,
        mime_type="image/png",
        status=ArtworkStatus.UPLOADED
    )
    
    try:
        session.add(art)
        session.commit()
        
        # Verify it was inserted correctly and matches UPLOADED
        db_art = session.execute(
            select(Artwork).where(Artwork.id == artwork_id)
        ).scalar_one_or_none()
        
        assert db_art is not None
        assert db_art.status == ArtworkStatus.UPLOADED
        
        # Clean up
        session.delete(art)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
