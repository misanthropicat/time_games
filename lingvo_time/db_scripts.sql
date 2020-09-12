DROP TABLE if exists lingvo_exercises;
drop table if exists runs;

CREATE table lingvo_exercises (
    ex_id primary key not null,
    run_id not null,
    word varchar(100),
    spaced integer,
    last_updated real,
    foreign key (run_id) references runs(run_id)
);

CREATE table runs (
    run_id not null primary key,
    run_created real,
    runtime real,
    play_time real
);