-- New empty installation only. Existing users: run upgrade.sql instead.
CREATE DATABASE IF NOT EXISTS student_attendance_system CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE student_attendance_system;
SET FOREIGN_KEY_CHECKS=0;

CREATE TABLE `ar_user` (
  `must_change_password` tinyint NOT NULL DEFAULT 1,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `name` varchar(100) NOT NULL,
  `title` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`email`),
  CONSTRAINT `chk_ar_title` CHECK ((`title` in (_utf8mb3'Mr',_utf8mb3'Mrs',_utf8mb3'Ms')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `class_session` (
  `updated_by` varchar(255) DEFAULT NULL,
  `date` date NOT NULL,
  `week_number` tinyint NOT NULL,
  `course_code` varchar(20) NOT NULL,
  `academic_year` varchar(9) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `special_medical_report` longblob,
  `updated_time` datetime DEFAULT NULL,
  PRIMARY KEY (`course_code`,`date`,`week_number`),
  KEY `course_code` (`course_code`),
  KEY `email` (`email`),
  KEY `fk_session_offering` (`course_code`,`academic_year`),
  CONSTRAINT `class_session_ibfk_1` FOREIGN KEY (`course_code`) REFERENCES `course` (`course_code`),
  CONSTRAINT `class_session_ibfk_2` FOREIGN KEY (`email`) REFERENCES `ar_user` (`email`),
  CONSTRAINT `fk_session_offering` FOREIGN KEY (`course_code`, `academic_year`) REFERENCES `course_offering` (`course_code`, `academic_year`),
  CONSTRAINT `chk_week_number` CHECK ((`week_number` between 1 and 14))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `course` (
  `course_code` varchar(20) NOT NULL,
  `study_year` tinyint NOT NULL,
  `semester_number` tinyint NOT NULL,
  PRIMARY KEY (`course_code`),
  KEY `academic_year` (`study_year`,`semester_number`),
  CONSTRAINT `chk_course_semester_number` CHECK ((`semester_number` in (1,2))),
  CONSTRAINT `chk_course_study_year` CHECK ((`study_year` between 1 and 4))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `course_offering` (
  `teaching_end` date DEFAULT NULL,
  `course_code` varchar(20) NOT NULL,
  `academic_year` varchar(9) NOT NULL,
  PRIMARY KEY (`course_code`,`academic_year`),
  CONSTRAINT `fk_offering_course` FOREIGN KEY (`course_code`) REFERENCES `course` (`course_code`),
  CONSTRAINT `chk_offering_academic_year` CHECK (regexp_like(`academic_year`,_utf8mb4'^[0-9]{2}/[0-9]{2}$'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `hod` (
  `email` varchar(255) NOT NULL,
  PRIMARY KEY (`email`),
  CONSTRAINT `fk_hod_lecturer` FOREIGN KEY (`email`) REFERENCES `lecturer` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `lecturer` (
  `must_change_password` tinyint NOT NULL DEFAULT 1,
  `email` varchar(255) NOT NULL,
  `type` varchar(50) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `name` varchar(100) NOT NULL,
  `title` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`email`),
  CONSTRAINT `chk_lecturer_type` CHECK ((`type` in (_utf8mb3'Lecturer',_utf8mb3'Visiting Lecturer',_utf8mb3'Temporary Lecturer',_utf8mb3'Demonstrator',_utf8mb3'Coordinator',_utf8mb3'Senior Lecturer',_utf8mb3'Assistant Lecturer')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `lecturer_course` (
  `email` varchar(255) NOT NULL,
  `course_code` varchar(20) NOT NULL,
  `academic_year` varchar(9) NOT NULL,
  PRIMARY KEY (`email`,`course_code`,`academic_year`),
  KEY `course_code` (`course_code`),
  KEY `fk_lecturer_course_offering` (`course_code`,`academic_year`),
  CONSTRAINT `fk_lecturer_course_offering` FOREIGN KEY (`course_code`, `academic_year`) REFERENCES `course_offering` (`course_code`, `academic_year`),
  CONSTRAINT `lecturer_course_ibfk_1` FOREIGN KEY (`email`) REFERENCES `lecturer` (`email`),
  CONSTRAINT `lecturer_course_ibfk_2` FOREIGN KEY (`course_code`) REFERENCES `course` (`course_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `semester` (
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `academic_year` varchar(9) NOT NULL,
  `study_year` tinyint NOT NULL,
  `semester_number` tinyint NOT NULL,
  PRIMARY KEY (`academic_year`,`study_year`,`semester_number`),
  CONSTRAINT `chk_academic_year_format` CHECK (regexp_like(`academic_year`,_utf8mb3'^[0-9]{2}/[0-9]{2}$')),
  CONSTRAINT `chk_semester_number` CHECK ((`semester_number` in (1,2))),
  CONSTRAINT `chk_study_year` CHECK ((`study_year` between 1 and 4))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `student` (
  `must_change_password` tinyint NOT NULL DEFAULT 1,
  `email` varchar(255) NOT NULL,
  `reg_number` varchar(30) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `name` varchar(100) NOT NULL,
  `title` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`email`),
  UNIQUE KEY `reg_number` (`reg_number`),
  CONSTRAINT `chk_student_reg_not_blank` CHECK ((char_length(trim(`reg_number`)) > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `student_class_session` (
  `email` varchar(255) NOT NULL,
  `course_code` varchar(20) NOT NULL,
  `date` date NOT NULL,
  `week_number` tinyint NOT NULL,
  `attendance_status` tinyint NOT NULL,
  `absent_reason` varchar(255) DEFAULT NULL,
  `medical_report` longblob,
  `medical_filename` varchar(100) DEFAULT NULL,
  `medical_mimetype` varchar(50) DEFAULT NULL,
  `medical_kind` varchar(10) DEFAULT NULL,
  `medical_status` varchar(10) DEFAULT NULL,
  `medical_submitted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`email`,`course_code`,`date`,`week_number`),
  KEY `date` (`date`,`week_number`),
  KEY `fk_attendance_class_session` (`course_code`,`date`,`week_number`),
  CONSTRAINT `fk_attendance_class_session` FOREIGN KEY (`course_code`, `date`, `week_number`) REFERENCES `class_session` (`course_code`, `date`, `week_number`),
  CONSTRAINT `student_class_session_ibfk_1` FOREIGN KEY (`email`) REFERENCES `student` (`email`),
  CONSTRAINT `chk_absent_reason` CHECK ((`absent_reason` in (_utf8mb4'MC',_utf8mb4'SMC',_utf8mb4'SRC',_utf8mb4'EXCUSE'))),
  CONSTRAINT `chk_attendance_status` CHECK ((`attendance_status` in (0,1)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `student_semester` (
  `email` varchar(255) NOT NULL,
  `academic_year` varchar(9) NOT NULL,
  `study_year` tinyint NOT NULL,
  `semester_number` tinyint NOT NULL,
  PRIMARY KEY (`email`,`academic_year`,`study_year`,`semester_number`),
  KEY `academic_year` (`academic_year`,`study_year`,`semester_number`),
  CONSTRAINT `student_semester_ibfk_1` FOREIGN KEY (`email`) REFERENCES `student` (`email`),
  CONSTRAINT `student_semester_ibfk_2` FOREIGN KEY (`academic_year`, `study_year`, `semester_number`) REFERENCES `semester` (`academic_year`, `study_year`, `semester_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS student_course (
 email varchar(255) NOT NULL,
 course_code varchar(20) NOT NULL,
 academic_year varchar(9) NOT NULL,
 PRIMARY KEY (email,course_code,academic_year),
 CONSTRAINT fk_student_course_student FOREIGN KEY (email) REFERENCES student(email),
 CONSTRAINT fk_student_course_offering FOREIGN KEY (course_code,academic_year) REFERENCES course_offering(course_code,academic_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
SET FOREIGN_KEY_CHECKS=1;
