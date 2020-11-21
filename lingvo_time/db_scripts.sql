drop table if exists lingvo_exercises;
drop table if exists math_exercises;
drop table if exists runs;

create table lingvo_exercises (
    ex_id primary key not null,
    run_id not null,
    word varchar(100),
    spaced integer,
    last_updated real,
    foreign key (run_id) references runs(run_id)
);

create table runs (
    run_id not null primary key,
    run_created real,
    runtime real,
    play_time_sec integer,
    game_type varchar(25),
    level real
);

create table math_exercises (
    ex_id not null primary key,
    run_id not null,
    task varchar(100),
    expected integer,
    last_updated real,
    foreign key (run_id) references runs(run_id)
)