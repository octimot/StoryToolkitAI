# Changelog

All notable changes to this project will be documented in this file, starting with version 0.17.7.

## [0.17.10] - 2023-02-19

### Added

- Ability to semantically search markers from project.json files using the "Advanced Search" button in the main window 

### Changed

- Advanced Search is now performed in a console-like window to improve functionality and to preserve search history
- Advanced Search window now has a Find function (Ctrl/CMD+F) to search for text in the window

## [0.17.9] - 2023-02-18

### Added

- Advanced search results of text files are now opened and highlighted in a new window
- Resolve timeline markers are now saved in the project.json file to allow future project-wide marker searches
- Groups button in transcription window opens up the groups window for that transcription (same as SHIFT+G)

### Changed

- Find function in transcripts is now moved to its own window (use Ctrl/CMD+F to open it)

## [0.17.8] - 2023-02-17

### Added

- Ability to search semantically in any .txt file on your machine using the "Advanced Search" button in the main window
- Advanced search caching for significantly faster searches
- Using --noresolve argument on main script disables Resolve API polling for that run

## [0.17.7] - 2023-02-08

### Changed

- Switched to new openai-whisper module which supports the large-v2 model

### Bugfixes

- Fixed a few Resolve API communication issues on timeline and project change