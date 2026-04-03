from application.services.structured_story_migration_service import StructuredStoryMigrationService


def main():
    result = StructuredStoryMigrationService().run()
    print(f"migrated_projects={result['migrated_projects']}, skipped={result['skipped']}")


if __name__ == "__main__":
    main()
