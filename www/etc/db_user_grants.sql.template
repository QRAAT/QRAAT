-- front-end database users
-- actually, frontend server database user grants only, for users and grants see ../frontend_db_users.sql

-- django admin controls django database
GRANT SELECT, INSERT, UPDATE, DELETE, INDEX, CREATE, DROP, ALTER ON django.* TO django_admin@'localhost';


-- web_reader has read-only access to both databases
GRANT SELECT ON django.* TO web_reader@'localhost';
GRANT SELECT ON qraat.* TO web_reader@'localhost';

-- web_writer can write to project metadata tables
GRANT SELECT, INSERT, UPDATE ON django.* TO web_writer@'localhost';
GRANT SELECT ON qraat.* TO web_writer@'localhost';
GRANT SELECT, INSERT, UPDATE ON qraat.auth_project_collaborator TO web_writer@'localhost';
GRANT SELECT, INSERT, UPDATE ON qraat.auth_project_viewer TO web_writer@'localhost';
GRANT SELECT, INSERT, UPDATE ON qraat.deployment TO web_writer@'localhost';
GRANT SELECT, INSERT, UPDATE ON qraat.location TO web_writer@'localhost';
GRANT SELECT, INSERT, UPDATE ON qraat.project TO web_writer@'localhost';
GRANT SELECT, INSERT, UPDATE ON qraat.target TO web_writer@'localhost';
GRANT SELECT, INSERT, UPDATE ON qraat.tx TO web_writer@'localhost';
GRANT SELECT, INSERT, UPDATE ON qraat.tx_make TO web_writer@'localhost';
GRANT SELECT, INSERT, UPDATE ON qraat.tx_make_parameters TO web_writer@'localhost';
GRANT SELECT, INSERT, UPDATE ON qraat.tx_parameters TO web_writer@'localhost';

